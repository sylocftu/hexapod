"""
PCA9685 16-channel PWM servo driver via I²C (smbus2).

I²C address : 0x40 (default, AD0–AD5 all low)
Oscillator  : 25 MHz internal
PWM freq    : 50 Hz (standard servo update rate)

Usage
-----
    driver = PCA9685(bus=1, address=0x40)
    driver.set_servo_angle(channel=0, angle_deg=90.0)
    driver.set_all_servos([90.0] * 18)

When the smbus2 library is not available (i.e. running on a desktop /
in tests), the driver automatically enters simulation mode and all
register writes are no-ops.
"""

import logging
import time

logger = logging.getLogger(__name__)

# ── Try to import smbus2; fall back to simulation ─────────────────────────────
try:
    import smbus2
    _SMBUS_AVAILABLE = True
except ImportError:
    _SMBUS_AVAILABLE = False
    logger.warning("smbus2 not available — PCA9685 running in simulation mode.")

# ── Register map ──────────────────────────────────────────────────────────────
_REG_MODE1 = 0x00
_REG_MODE2 = 0x01
_REG_PRESCALE = 0xFE
_REG_LED0_ON_L = 0x06   # First channel ON  low byte; subsequent channels +4
_REG_LED0_ON_H = 0x07
_REG_LED0_OFF_L = 0x08  # First channel OFF low byte
_REG_LED0_OFF_H = 0x09
_REG_ALL_LED_ON_L = 0xFA
_REG_ALL_LED_OFF_L = 0xFC

_MODE1_RESTART = 0x80
_MODE1_SLEEP = 0x10
_MODE1_ALLCALL = 0x01
_MODE1_AI = 0x20       # Auto-increment register address

_INTERNAL_OSCILLATOR_HZ = 25_000_000
_PWM_RESOLUTION = 4096             # 12-bit PWM


class PCA9685:
    """PCA9685 PWM servo driver.

    Parameters
    ----------
    bus : int
        I²C bus number (1 on Raspberry Pi).
    address : int
        I²C address (default 0x40).
    freq_hz : int
        PWM frequency in Hz (default 50 for servos).
    """

    def __init__(
        self,
        bus: int = 1,
        address: int = 0x40,
        freq_hz: int = 50,
    ) -> None:
        self.address = address
        self.freq_hz = freq_hz
        self._simulation = not _SMBUS_AVAILABLE
        self._offsets = [0.0] * 16   # per-channel calibration offsets (degrees)

        if not self._simulation:
            try:
                self._bus = smbus2.SMBus(bus)
                self._reset_chip()
                self._set_frequency(freq_hz)
            except Exception as exc:
                logger.warning("PCA9685 hardware init failed (%s); using simulation.", exc)
                self._simulation = True

    # ── Low-level I²C helpers ─────────────────────────────────────────────────

    def _write(self, register: int, value: int) -> None:
        if self._simulation:
            return
        self._bus.write_byte_data(self.address, register, value)

    def _read(self, register: int) -> int:
        if self._simulation:
            return 0
        return self._bus.read_byte_data(self.address, register)

    # ── Initialisation ────────────────────────────────────────────────────────

    def _reset_chip(self) -> None:
        """Perform software reset of the PCA9685."""
        self._write(_REG_MODE1, 0x00)   # clear any previous state
        time.sleep(0.005)

    def _set_frequency(self, freq_hz: int) -> None:
        """Set the PWM oscillator prescale for the desired frequency."""
        # prescale = round(f_osc / (4096 * freq)) - 1
        prescale = round(_INTERNAL_OSCILLATOR_HZ / (_PWM_RESOLUTION * freq_hz)) - 1
        prescale = max(3, min(255, prescale))

        # Must put chip to sleep before changing prescale
        old_mode = self._read(_REG_MODE1)
        self._write(_REG_MODE1, (old_mode & 0x7F) | _MODE1_SLEEP)
        self._write(_REG_PRESCALE, prescale)
        self._write(_REG_MODE1, old_mode)
        time.sleep(0.005)
        # Set RESTART and AUTO-INCREMENT bits
        self._write(_REG_MODE1, old_mode | _MODE1_RESTART | _MODE1_AI)

    # ── PWM output ────────────────────────────────────────────────────────────

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        """Set raw PWM on/off counts for one channel.

        Parameters
        ----------
        channel : int
            Channel index 0–15.
        on : int
            Tick count (0–4095) at which output goes high.
        off : int
            Tick count (0–4095) at which output goes low.
        """
        if not 0 <= channel <= 15:
            raise ValueError(f"Channel must be 0–15, got {channel}.")
        base = _REG_LED0_ON_L + 4 * channel
        self._write(base, on & 0xFF)
        self._write(base + 1, on >> 8)
        self._write(base + 2, off & 0xFF)
        self._write(base + 3, off >> 8)

    def set_servo_angle(
        self,
        channel: int,
        angle_deg: float,
        min_pulse_us: float = 500.0,
        max_pulse_us: float = 2500.0,
    ) -> None:
        """Set a servo to the specified angle in degrees.

        Parameters
        ----------
        channel : int
            Servo channel 0–17.  (Channels >15 are ignored in simulation;
            ensure your physical wiring matches.)
        angle_deg : float
            Target angle 0–180 degrees.
        min_pulse_us : float
            Pulse width at 0° in microseconds (default 500 µs).
        max_pulse_us : float
            Pulse width at 180° in microseconds (default 2500 µs).
        """
        ch_idx = channel % 16   # PCA9685 has 16 channels; use modulo for safety

        # Apply calibration offset
        angle_deg = max(0.0, min(180.0, angle_deg + self._offsets[ch_idx]))

        # Map angle → pulse width in µs
        pulse_us = min_pulse_us + (max_pulse_us - min_pulse_us) * angle_deg / 180.0

        # Map pulse width → 12-bit tick count
        period_us = 1_000_000.0 / self.freq_hz
        off_count = round(pulse_us / period_us * _PWM_RESOLUTION)
        off_count = max(0, min(_PWM_RESOLUTION - 1, off_count))

        self.set_pwm(ch_idx, 0, off_count)

    def set_all_servos(self, angles: list) -> None:
        """Set all servo channels at once.

        Parameters
        ----------
        angles : list[float]
            List of up to 18 angles in degrees.  Missing channels are set
            to 90° (neutral).
        """
        for ch, angle in enumerate(angles[:18]):
            self.set_servo_angle(ch, angle)

    def reset(self) -> None:
        """Return all 18 servo channels to the 90° neutral position."""
        self.set_all_servos([90.0] * 18)

    def set_offset(self, channel: int, offset_deg: float) -> None:
        """Set a calibration trim offset for one channel.

        Useful for correcting manufacturing variation in servo horns.

        Parameters
        ----------
        channel : int
            Channel 0–15.
        offset_deg : float
            Offset in degrees (added to all subsequent angle commands).
        """
        if not 0 <= channel <= 15:
            raise ValueError(f"Channel must be 0–15, got {channel}.")
        self._offsets[channel] = offset_deg

    def close(self) -> None:
        """Release the I²C bus."""
        if not self._simulation:
            try:
                self._bus.close()
            except Exception:
                pass
