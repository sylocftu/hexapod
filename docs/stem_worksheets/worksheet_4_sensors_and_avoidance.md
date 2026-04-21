# Worksheet 4: Sensors and Obstacle Avoidance

**Subject:** Physics + Robotics  
**Grade level:** 9–12  
**Estimated time:** 55 minutes  
**Prerequisite knowledge:** Worksheets 1–3; basic Python

---

## Learning Objectives

1. Explain how the HC-SR04 ultrasonic sensor measures distance.
2. Calculate distance from echo pulse time using the speed of sound.
3. Calibrate a sensor and identify sources of error.
4. Write a simple obstacle avoidance algorithm in Python.
5. Describe how the MPU-6050 IMU can detect slopes.

---

## Background: How HC-SR04 Works

The HC-SR04 sensor emits a **burst of 8 ultrasonic pulses** at 40 kHz.
Sound travels through air until it hits an object and bounces back.
The sensor measures the **time** between transmitting and receiving the echo.

```
HC-SR04
┌──────────┐
│  T    E  │      Ultrasonic pulse →         ← Echo
│ (TX) (RX)│═══════════════════════) WALL )═══
└──────────┘

T = trigger pulse (10 µs HIGH → starts transmission)
E = echo pulse (HIGH for duration = travel time)
```

### Distance Formula

$$d = \frac{v_s \times t}{2}$$

Where:
- `d` = distance to object (metres)
- `v_s` = speed of sound ≈ 343 m/s at 20°C
- `t` = echo pulse duration (seconds)
- The factor of **2** accounts for the round trip (out and back)

---

## Exercise 4.1: Calculate Distance from Pulse Time

Fill in the table.  Use `v_s = 343 m/s`.

| Echo pulse time (µs) | Echo pulse time (s) | Distance (m) | Distance (cm) |
|---|---|---|---|
| 293 µs | 0.000293 s | _______ | _______ |
| 876 µs | _______ | _______ | _______ |
| 1751 µs | _______ | _______ | _______ |
| 5831 µs | _______ | _______ | _______ |

**Hint for row 1:**  
`d = (343 × 0.000293) / 2 = 0.0502 m = 5.02 cm`

---

## Exercise 4.2: Effect of Temperature on Speed of Sound

The speed of sound changes with temperature:

$$v_s \approx 331.3 + 0.606 \times T \quad [\text{m/s}]$$

where T is the temperature in °C.

| Temperature (°C) | Speed of sound (m/s) | Error vs. 20°C calibration (%) |
|---|---|---|
| 0 °C | _______ | _______ |
| 20 °C | _______ | 0 % |
| 35 °C | _______ | _______ |
| 50 °C | _______ | _______ |

**Question:** If the robot is calibrated at 20°C but operates at 35°C,
will measured distances be over-estimated or under-estimated?  Why?

_________________________________________________________________________

---

## Exercise 4.3: Reading from the SensorArray

```python
from hexapod_core.hardware import SensorArray

# Create a sensor array with default GPIO pins
# (In simulation mode on desktop — returns fixed distances)
sensors = SensorArray.create_hcsr04_triplet()

distances = sensors.scan()
print(f"Left:   {distances[0]:.1f} cm")
print(f"Center: {distances[1]:.1f} cm")
print(f"Right:  {distances[2]:.1f} cm")
```

**Record values (simulation mode returns 50 cm by default):**

| Sensor | Distance (cm) |
|---|---|
| Left | _______ |
| Center | _______ |
| Right | _______ |

---

## Coding Activity: Simple Obstacle Avoidance

Write a function `avoid_obstacles(distances)` that:

- If center distance < 30 cm → turn right (omega = -45 deg/s)
- Else if left distance < 25 cm → turn right (omega = -30 deg/s)
- Else if right distance < 25 cm → turn left (omega = +30 deg/s)
- Else → go forward (vx = 0.05 m/s, omega = 0)

```python
import requests

BASE = "http://localhost:8000"

def avoid_obstacles(distances):
    left, center, right = distances

    # ── Fill in the logic below ──────────────────────────────────────────
    if center < 30:
        vx, vy, omega = 0.0, 0.0, ___
    elif ___:
        vx, vy, omega = ___, ___, ___
    elif ___:
        vx, vy, omega = ___, ___, ___
    else:
        vx, vy, omega = ___, ___, ___
    # ────────────────────────────────────────────────────────────────────

    requests.post(f"{BASE}/velocity",
                  json={"vx": vx, "vy": vy, "omega": omega})

# Main loop (10 Hz)
import time
from hexapod_core.hardware import SensorArray
sensors = SensorArray.create_hcsr04_triplet()

requests.post(f"{BASE}/gait/tripod")   # start moving

while True:
    d = sensors.scan()
    avoid_obstacles(d)
    time.sleep(0.1)
```

**Test questions:**
1. What happens if all three sensors read < 25 cm simultaneously?
2. How could you make the robot back up instead of turning?
3. What distance threshold would you use for a narrow corridor?

---

## Extension: IMU Slope Detection

The MPU-6050 measures acceleration along three axes.  When the robot is stationary:

- On flat ground: `az ≈ 9.81 m/s²`, `ax ≈ ay ≈ 0`
- On a slope (tilted forward by θ): `ax = g·sin(θ)`, `az = g·cos(θ)`

### Roll and Pitch from Accelerometer

$$\text{roll} = \text{atan2}(a_y, a_z)$$
$$\text{pitch} = \text{atan2}(-a_x, \sqrt{a_y^2 + a_z^2})$$

```python
from hexapod_core.hardware import MPU6050
import math, time

imu = MPU6050()

for _ in range(20):
    ax, ay, az = imu.read_accel()
    roll  = math.degrees(math.atan2(ay, az))
    pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
    print(f"Roll: {roll:6.1f}°   Pitch: {pitch:6.1f}°")
    time.sleep(0.1)
```

**Extension challenge:** Use pitch angle to automatically adjust body height —
raise the front of the body when going uphill so the legs don't drag.

Sketch the control loop (input → decision → output):

```
[ IMU pitch ] → [ if pitch > ___° ] → [ adjust body height ]
                 [ else            ] → [ no change          ]
```

---

## Vocabulary

| Term | Definition |
|---|---|
| HC-SR04 | Ultrasonic distance sensor using sound echoes |
| Ultrasonic | Sound above 20 kHz (inaudible to humans) |
| Echo | Reflected sound wave |
| Speed of sound | ≈ 343 m/s at 20°C in air |
| Duty cycle | Fraction of time a digital signal is HIGH |
| MPU-6050 | 6-axis IMU: 3-axis accelerometer + 3-axis gyroscope |
| Accelerometer | Sensor measuring linear acceleration |
| Gyroscope | Sensor measuring rotational rate |
| Complementary filter | Blend of gyro and accel data for stable angle estimate |
| Obstacle avoidance | Algorithm that steers around detected obstacles |

---

*Next worksheet: Worksheet 5 — Docker and DevOps*
