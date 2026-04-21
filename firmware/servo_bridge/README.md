# Servo Bridge Firmware

Optional co-processor firmware for Arduino or ESP32 that acts as a serial-to-PWM bridge.

## Purpose

In some configurations it is useful to have a microcontroller handle the PWM generation
rather than the PCA9685 I²C driver.  This sketch listens on the hardware serial port for
simple text commands and drives up to 18 servos directly.

## Supported Boards

| Board | Notes |
|---|---|
| Arduino Mega 2560 | Enough PWM pins; tested |
| Arduino Uno R3 | Fewer pins; adequate for 6 servos |
| ESP32 DevKitC | Wi-Fi bonus; use hardware serial on pins 16/17 |

## Wiring

| Arduino Pin | Function |
|---|---|
| D2–D19 | Servo signal wires (channels 0–17) |
| 5V | Servo VCC (short runs only; use BEC for >4 servos) |
| GND | Common ground with Raspberry Pi |
| RX0 (D0) | Connected to Pi TX (GPIO14 / pin 8) |
| TX0 (D1) | Connected to Pi RX (GPIO15 / pin 10) |

> **Logic level:** Arduino runs at 5 V; Raspberry Pi at 3.3 V.
> Use a level shifter on the TX line from the Arduino to the Pi RX.

## Flashing Instructions

1. Install [Arduino IDE 2.x](https://www.arduino.cc/en/software).
2. Open `servo_bridge.ino`.
3. Select board: **Tools → Board → Arduino Mega** (or your board).
4. Select port: **Tools → Port → /dev/ttyUSB0** (or COM port on Windows).
5. Click **Upload** (Ctrl+U).
6. Open Serial Monitor at **115200 baud** to test.

## Serial Protocol

Communication is plain ASCII over UART at **115200 baud, 8N1**.

### Set servo angle

```
C<channel> <angle>\n
```

- `<channel>` — integer 0–17
- `<angle>` — integer 0–180 (degrees)
- `\n` — newline terminator (LF, `0x0A`)

**Example:** Set channel 3 to 90°

```
C3 90\n
```

**Response:**

```
OK\n
```

### Error response

If the command cannot be parsed or the channel/angle is out of range:

```
ERR\n
```

### Query firmware version

```
V\n
```

**Response:**

```
servo_bridge v1.0\n
```

## Python Example

```python
import serial, time

port = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
time.sleep(2)  # wait for Arduino reset

port.write(b'C0 90\n')
resp = port.readline()  # b'OK\n'
print(resp)
```
