# Hexapod Wiring Notes

## ⚠️ Safety First

- **Never charge LiPo batteries unattended.**
- Always connect a **fuse (10 A)** inline with the battery positive terminal.
- Power-on sequence: connect battery → wait 2 s → power on Raspberry Pi.
- Power-off sequence: shut down Raspberry Pi (`sudo shutdown -h now`) → disconnect battery.
- Keep LiPo voltage above **6.8 V** (3.4 V per cell) to prevent damage.

---

## Power Architecture

```
  [7.4V LiPo 5000mAh]
         │
      XT60 plug
         │
    [10A Fuse]
         │
    ┌────┴─────────┐
    │              │
[BEC 6V 10A]  [BEC 5V 5A]
    │              │
[Servo Power  [Logic Power
 Bus Rail]     Bus Rail]
    │              │
18×MG996R    ┌─────┴──────┐
             │            │
         [Pi 4 5V]  [PCA9685 VCC]
                    [MPU-6050 VCC]
                    [HC-SR04 VCC (via 5V)]
```

The servo BEC (6 V) connects to the V+ and GND rails on the PCA9685 terminal block.
The logic BEC (5 V) feeds the Raspberry Pi 4 via its USB-C port (or 5 V GPIO pin).

---

## Raspberry Pi 4 GPIO Pinout (Used Pins)

| GPIO (BCM) | Physical Pin | Function | Connected To |
|---|---|---|---|
| 2 (SDA1) | 3 | I²C SDA | PCA9685 SDA, MPU-6050 SDA |
| 3 (SCL1) | 5 | I²C SCL | PCA9685 SCL, MPU-6050 SCL |
| 5 | 29 | HC-SR04 TRIG (center) | Center sensor TRIG |
| 6 | 31 | HC-SR04 ECHO (center) | Center sensor ECHO (via level shifter) |
| 17 | 11 | HC-SR04 TRIG (left) | Left sensor TRIG |
| 27 | 13 | HC-SR04 ECHO (left) | Left sensor ECHO (via level shifter) |
| 22 | 15 | HC-SR04 TRIG (right) | Right sensor TRIG |
| 23 | 16 | HC-SR04 ECHO (right) | Right sensor ECHO (via level shifter) |
| — | 2 | 5V power | BEC 5V out |
| — | 6 | GND | Common ground |

> **Note:** HC-SR04 ECHO is 5 V logic.  Use a 4-channel level shifter between
> the sensor echo pins and the Raspberry Pi GPIO.

---

## I²C Bus Layout

```
Raspberry Pi (I²C bus 1, /dev/i2c-1)
    SDA ──┬─────────────────────┐
    SCL ──┤                     │
          │                     │
     [PCA9685 0x40]       [MPU-6050 0x68]
     (servo driver)         (IMU)
```

| Device | I²C Address | Notes |
|---|---|---|
| PCA9685 | 0x40 | AD0–AD5 all low (default) |
| MPU-6050 | 0x68 | AD0 pin low (default) |

Enable I²C on the Pi: `sudo raspi-config` → Interface Options → I2C → Enable.

---

## Servo Channel Mapping (PCA9685)

Leg numbering (top-down view):

```
     FRONT
  Leg0   Leg1
Leg2       Leg3
  Leg4   Leg5
      BACK
```

| Leg | Side | Coxa Ch | Femur Ch | Tibia Ch |
|---|---|---|---|---|
| 0 | Front-Left | 0 | 1 | 2 |
| 1 | Front-Right | 3 | 4 | 5 |
| 2 | Mid-Left | 6 | 7 | 8 |
| 3 | Mid-Right | 9 | 10 | 11 |
| 4 | Rear-Left | 12 | 13 | 14 |
| 5 | Rear-Right | 15 | 16 | 17 |

**Convention:** 90° = neutral (servo horn horizontal). Increase angle → clockwise.

---

## Ultrasonic Sensor GPIO Pins

| Sensor | TRIG (BCM) | ECHO (BCM) | Notes |
|---|---|---|---|
| Center | 5 | 6 | Forward-facing |
| Left | 17 | 27 | 45° left |
| Right | 22 | 23 | 45° right |

Wire TRIG directly from Pi GPIO (3.3 V output is accepted by HC-SR04).
Wire ECHO through a **voltage divider or level shifter** — the echo is 5 V!

---

## Common Ground

All grounds **must** be tied together:
- LiPo GND
- BEC 5 V GND
- BEC 6 V GND
- Raspberry Pi GND
- PCA9685 GND
- MPU-6050 GND
- All HC-SR04 GND pins

Use a PCB prototype board as a ground bus.
