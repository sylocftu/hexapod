"""
MPU-6050 6-axis IMU driver via I²C (smbus2).

I²C address : 0x68 (AD0 pin low, default)
              0x69 (AD0 pin high)

Provides
--------
- Raw accelerometer (m/s²) and gyroscope (deg/s) readings
- Temperature in °C
- Complementary filter for roll and pitch estimation

When smbus2 is unavailable the driver enters simulation mode and returns
zero / identity values.
"""

import logging
import math
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import smbus2
    _SMBUS_AVAILABLE = True
except ImportError:
    _SMBUS_AVAILABLE = False
    logger.warning("smbus2 not available — MPU6050 running in simulation mode.")

# ── Register map ──────────────────────────────────────────────────────────────
_REG_PWR_MGMT_1 = 0x6B
_REG_SMPLRT_DIV = 0x19
_REG_CONFIG = 0x1A
_REG_GYRO_CONFIG = 0x1B
_REG_ACCEL_CONFIG = 0x1C
_REG_ACCEL_XOUT_H = 0x3B
_REG_TEMP_OUT_H = 0x41
_REG_GYRO_XOUT_H = 0x43
_REG_WHO_AM_I = 0x75

# Scale factors
_ACCEL_SCALE_2G = 16384.0     # LSB / g  (±2 g default)
_GYRO_SCALE_250 = 131.0       # LSB / (deg/s) (±250°/s default)
_GRAVITY = 9.80665            # m/s²


@dataclass
class ImuData:
    """Single IMU reading snapshot."""

    ax: float = 0.0    # Acceleration X  (m/s²)
    ay: float = 0.0    # Acceleration Y  (m/s²)
    az: float = 0.0    # Acceleration Z  (m/s²)
    gx: float = 0.0    # Gyroscope X     (deg/s)
    gy: float = 0.0    # Gyroscope Y     (deg/s)
    gz: float = 0.0    # Gyroscope Z     (deg/s)
    temp_c: float = 0.0  # Die temperature (°C)


class MPU6050:
    """MPU-6050 IMU driver with complementary filter.

    Parameters
    ----------
    bus : int
        I²C bus number (1 on Raspberry Pi).
    address : int
        I²C address (0x68 default, 0x69 if AD0 high).
    alpha : float
        Complementary filter weight [0, 1].  Higher → trust gyro more.
    """

    def __init__(
        self,
        bus: int = 1,
        address: int = 0x68,
        alpha: float = 0.96,
    ) -> None:
        self.address = address
        self.alpha = alpha
        self._simulation = not _SMBUS_AVAILABLE
        self._roll: float = 0.0
        self._pitch: float = 0.0
        self._last_time: float = time.monotonic()

        if not self._simulation:
            try:
                self._bus = smbus2.SMBus(bus)
                self._init_device()
            except Exception as exc:
                logger.warning("MPU6050 hardware init failed (%s); using simulation.", exc)
                self._simulation = True

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_device(self) -> None:
        """Wake the MPU-6050 and configure ranges."""
        # Clear sleep bit
        self._bus.write_byte_data(self.address, _REG_PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        # Set sample rate to 100 Hz (divider = 9 for 1 kHz internal clock)
        self._bus.write_byte_data(self.address, _REG_SMPLRT_DIV, 9)
        # DLPF config: ~44 Hz bandwidth
        self._bus.write_byte_data(self.address, _REG_CONFIG, 0x03)
        # Gyro ±250°/s
        self._bus.write_byte_data(self.address, _REG_GYRO_CONFIG, 0x00)
        # Accel ±2 g
        self._bus.write_byte_data(self.address, _REG_ACCEL_CONFIG, 0x00)

    # ── Read helpers ──────────────────────────────────────────────────────────

    def _read_word_signed(self, reg: int) -> int:
        """Read a big-endian signed 16-bit integer from two consecutive registers."""
        high = self._bus.read_byte_data(self.address, reg)
        low = self._bus.read_byte_data(self.address, reg + 1)
        value = (high << 8) | low
        if value >= 0x8000:
            value -= 0x10000
        return value

    # ── Public API ────────────────────────────────────────────────────────────

    def read_accel(self) -> tuple:
        """Return (ax, ay, az) in m/s²."""
        if self._simulation:
            return (0.0, 0.0, _GRAVITY)
        ax_raw = self._read_word_signed(_REG_ACCEL_XOUT_H)
        ay_raw = self._read_word_signed(_REG_ACCEL_XOUT_H + 2)
        az_raw = self._read_word_signed(_REG_ACCEL_XOUT_H + 4)
        scale = _GRAVITY / _ACCEL_SCALE_2G
        return (ax_raw * scale, ay_raw * scale, az_raw * scale)

    def read_gyro(self) -> tuple:
        """Return (gx, gy, gz) in deg/s."""
        if self._simulation:
            return (0.0, 0.0, 0.0)
        gx_raw = self._read_word_signed(_REG_GYRO_XOUT_H)
        gy_raw = self._read_word_signed(_REG_GYRO_XOUT_H + 2)
        gz_raw = self._read_word_signed(_REG_GYRO_XOUT_H + 4)
        return (
            gx_raw / _GYRO_SCALE_250,
            gy_raw / _GYRO_SCALE_250,
            gz_raw / _GYRO_SCALE_250,
        )

    def read_temperature(self) -> float:
        """Return die temperature in °C."""
        if self._simulation:
            return 25.0
        raw = self._read_word_signed(_REG_TEMP_OUT_H)
        return raw / 340.0 + 36.53

    def read(self) -> ImuData:
        """Return a full ImuData snapshot."""
        ax, ay, az = self.read_accel()
        gx, gy, gz = self.read_gyro()
        temp = self.read_temperature()
        return ImuData(ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz, temp_c=temp)

    def get_attitude(self) -> tuple:
        """Return (roll_deg, pitch_deg) using a complementary filter.

        Combines accelerometer (long-term stable) and gyroscope (short-term
        accurate) measurements.  Must be called regularly for accurate results.

        Returns
        -------
        (roll_deg, pitch_deg) : tuple[float, float]
        """
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now

        ax, ay, az = self.read_accel()
        gx, gy, _ = self.read_gyro()

        # Accelerometer-derived angles (noisy but drift-free)
        accel_roll = math.degrees(math.atan2(ay, az))
        accel_pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))

        if dt > 0:
            # Gyroscope integration (fast but drifts)
            gyro_roll = self._roll + gx * dt
            gyro_pitch = self._pitch + gy * dt

            # Complementary filter: blend gyro and accel estimates
            self._roll = self.alpha * gyro_roll + (1.0 - self.alpha) * accel_roll
            self._pitch = self.alpha * gyro_pitch + (1.0 - self.alpha) * accel_pitch

        return (self._roll, self._pitch)

    def close(self) -> None:
        """Release the I²C bus."""
        if not self._simulation:
            try:
                self._bus.close()
            except Exception:
                pass
