"""
Sensor drivers for the hexapod robot.

Includes
--------
- UltrasonicSensor  : HC-SR04 via RPi.GPIO (with mock fallback)
- VL53L0XSensor     : VL53L0X ToF sensor via I²C (with mock fallback)
- SensorArray       : Aggregate manager for multiple distance sensors

All drivers fall back to mock/simulation mode when their underlying
hardware library (RPi.GPIO / smbus2) is not importable.
"""

import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── GPIO availability ─────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available — ultrasonic sensors in simulation mode.")

# ── smbus2 availability ───────────────────────────────────────────────────────
try:
    import smbus2
    _SMBUS_AVAILABLE = True
except ImportError:
    _SMBUS_AVAILABLE = False


# ── HC-SR04 Ultrasonic Sensor ─────────────────────────────────────────────────

_SPEED_OF_SOUND_CM_S = 34300.0   # ~343 m/s at 20 °C
_ECHO_TIMEOUT_S = 0.03           # 30 ms max wait (≈ 5 m range)


class UltrasonicSensor:
    """HC-SR04 ultrasonic distance sensor.

    STEM note
    ---------
    The HC-SR04 sends a burst of 8 ultrasonic pulses at 40 kHz and measures
    how long the echo takes to return.  Distance = (time × speed of sound) / 2.
    The factor of 2 is because the sound travels to the object AND back.

    Parameters
    ----------
    trigger_pin : int
        BCM GPIO pin number connected to TRIG.
    echo_pin : int
        BCM GPIO pin number connected to ECHO (via level shifter!).
    simulation_distance_cm : float
        Fixed distance returned in simulation mode.
    """

    def __init__(
        self,
        trigger_pin: int,
        echo_pin: int,
        simulation_distance_cm: float = 50.0,
    ) -> None:
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self._sim_distance = simulation_distance_cm
        self._simulation = not _GPIO_AVAILABLE

        if not self._simulation:
            GPIO.setup(trigger_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)
            GPIO.output(trigger_pin, GPIO.LOW)
            time.sleep(0.05)  # settling time

    def measure_cm(self) -> float:
        """Return distance to nearest object in centimetres.

        Returns the simulated value when GPIO is not available.
        Returns -1.0 on timeout (object too far or sensor fault).
        """
        if self._simulation:
            return self._sim_distance

        # Send 10 µs trigger pulse
        GPIO.output(self.trigger_pin, GPIO.HIGH)
        time.sleep(10e-6)
        GPIO.output(self.trigger_pin, GPIO.LOW)

        # Wait for echo rising edge (start of echo pulse)
        deadline = time.monotonic() + _ECHO_TIMEOUT_S
        while GPIO.input(self.echo_pin) == 0:
            if time.monotonic() > deadline:
                return -1.0
        pulse_start = time.monotonic()

        # Wait for echo falling edge (end of echo pulse)
        deadline = time.monotonic() + _ECHO_TIMEOUT_S
        while GPIO.input(self.echo_pin) == 1:
            if time.monotonic() > deadline:
                return -1.0
        pulse_end = time.monotonic()

        elapsed = pulse_end - pulse_start
        distance_cm = elapsed * _SPEED_OF_SOUND_CM_S / 2.0
        return round(distance_cm, 1)

    def cleanup(self) -> None:
        """Release GPIO resources."""
        if not self._simulation:
            GPIO.cleanup([self.trigger_pin, self.echo_pin])


# ── VL53L0X Time-of-Flight Sensor ─────────────────────────────────────────────

_VL53L0X_DEFAULT_ADDRESS = 0x29
_REG_IDENTIFICATION_MODEL_ID = 0xC0
_REG_RESULT_RANGE_STATUS = 0x14


class VL53L0XSensor:
    """VL53L0X laser time-of-flight distance sensor via I²C.

    Provides shorter-range (~2 m), more accurate measurements than HC-SR04.
    Falls back to simulation mode when smbus2 is unavailable.

    Parameters
    ----------
    bus : int
        I²C bus number.
    address : int
        I²C address (default 0x29).
    simulation_distance_mm : int
        Fixed distance returned in simulation mode.
    """

    def __init__(
        self,
        bus: int = 1,
        address: int = _VL53L0X_DEFAULT_ADDRESS,
        simulation_distance_mm: int = 300,
    ) -> None:
        self.address = address
        self._sim_distance = simulation_distance_mm
        self._simulation = not _SMBUS_AVAILABLE

        if not self._simulation:
            try:
                self._bus = smbus2.SMBus(bus)
                # Minimal init: just verify WHO_AM_I
                model_id = self._bus.read_byte_data(address, _REG_IDENTIFICATION_MODEL_ID)
                if model_id != 0xEE:
                    logger.warning("VL53L0X WHO_AM_I unexpected (0x%02X); may not work.", model_id)
            except Exception as exc:
                logger.warning("VL53L0X init failed (%s); using simulation.", exc)
                self._simulation = True

    def measure_mm(self) -> int:
        """Return distance in millimetres.

        Returns -1 on error or when sensor is not ready.
        """
        if self._simulation:
            return self._sim_distance

        try:
            # Read 12-byte result register block starting at 0x14
            data = self._bus.read_i2c_block_data(self.address, _REG_RESULT_RANGE_STATUS, 12)
            # Range result is at bytes 10–11
            distance_mm = (data[10] << 8) | data[11]
            return distance_mm
        except Exception:
            return -1

    def close(self) -> None:
        """Release I²C bus."""
        if not self._simulation:
            try:
                self._bus.close()
            except Exception:
                pass


# ── SensorArray ───────────────────────────────────────────────────────────────


class SensorArray:
    """Aggregate manager for multiple distance sensors.

    Parameters
    ----------
    sensors : list
        Ordered list of sensor objects (UltrasonicSensor or VL53L0XSensor).
        Conventionally: [left, center, right].
    """

    def __init__(self, sensors: Optional[List] = None) -> None:
        self._sensors = sensors or []

    @classmethod
    def create_hcsr04_triplet(
        cls,
        pins: Optional[List] = None,
    ) -> "SensorArray":
        """Factory: create a 3-sensor HC-SR04 array with default GPIO pins.

        Default pins (BCM): center=TRIG5/ECHO6, left=TRIG17/ECHO27, right=TRIG22/ECHO23

        Parameters
        ----------
        pins : list of (trig, echo) tuples, optional
            Override default pins.
        """
        default_pins = [(5, 6), (17, 27), (22, 23)]
        pin_list = pins or default_pins
        sensors = [
            UltrasonicSensor(trigger_pin=t, echo_pin=e)
            for t, e in pin_list
        ]
        return cls(sensors=sensors)

    def scan(self) -> List[float]:
        """Return a list of distances (cm or mm, matching sensor type) for all sensors.

        Returns -1.0 for sensors that timed out or failed.
        """
        results = []
        for sensor in self._sensors:
            if isinstance(sensor, UltrasonicSensor):
                results.append(sensor.measure_cm())
            elif isinstance(sensor, VL53L0XSensor):
                results.append(float(sensor.measure_mm()))
            else:
                results.append(-1.0)
        return results

    def add_sensor(self, sensor) -> None:
        """Append a sensor to the array."""
        self._sensors.append(sensor)

    def cleanup(self) -> None:
        """Release all sensor resources."""
        for sensor in self._sensors:
            if hasattr(sensor, "cleanup"):
                sensor.cleanup()
            elif hasattr(sensor, "close"):
                sensor.close()
