/*
 * servo_bridge.ino
 * ----------------
 * STEM Hexapod Project — Serial-to-PWM servo bridge
 *
 * Listens on the hardware serial port (115200 baud) for simple text
 * commands and drives up to 18 servos via the Arduino Servo library.
 *
 * Command format:  "C<channel> <angle>\n"
 *   - channel : 0–17
 *   - angle   : 0–180 degrees
 *
 * Response:
 *   "OK\n"  on success
 *   "ERR\n" on bad command / out-of-range values
 *
 * Version query: "V\n" → "servo_bridge v1.0\n"
 *
 * STEM note:
 *   A servo motor has three wires: power (red), ground (brown/black),
 *   and signal (orange/yellow/white).  The signal wire receives a PWM
 *   (Pulse-Width Modulation) pulse every 20 ms.  The width of the pulse
 *   — between 500 µs and 2500 µs — tells the servo what angle to hold.
 *   This sketch converts a simple number (0–180) into that pulse width.
 */

#include <Servo.h>

// ── Configuration ────────────────────────────────────────────────────────────

#define NUM_SERVOS     18
#define SERIAL_BAUD    115200
#define INPUT_BUF_LEN  32

// First Arduino pin used for servo signal wires.
// Servos are wired to consecutive pins starting here.
// Arduino Mega: digital pins 2–19 are all capable of PWM via Servo library.
#define FIRST_SERVO_PIN 2

// Pulse width limits in microseconds (calibrate to your MG996R batch)
#define MIN_PULSE_US   500
#define MAX_PULSE_US   2500

// ── Globals ───────────────────────────────────────────────────────────────────

Servo servos[NUM_SERVOS];

// Input buffer for incoming serial characters
char inputBuf[INPUT_BUF_LEN];
uint8_t inputLen = 0;

// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(SERIAL_BAUD);

    // Attach all servos to consecutive digital pins and centre them at 90°
    for (int ch = 0; ch < NUM_SERVOS; ch++) {
        servos[ch].attach(
            FIRST_SERVO_PIN + ch,
            MIN_PULSE_US,
            MAX_PULSE_US
        );
        servos[ch].write(90);  // centre position
    }

    Serial.println(F("servo_bridge v1.0 ready"));
}

// ── Main loop ─────────────────────────────────────────────────────────────────

void loop() {
    // Read characters from serial one at a time
    while (Serial.available() > 0) {
        char c = (char)Serial.read();

        if (c == '\n' || c == '\r') {
            // End of command — process it
            if (inputLen > 0) {
                inputBuf[inputLen] = '\0';  // null-terminate
                processCommand(inputBuf);
                inputLen = 0;
            }
        } else {
            // Accumulate character; protect against buffer overflow
            if (inputLen < INPUT_BUF_LEN - 1) {
                inputBuf[inputLen++] = c;
            }
        }
    }
}

// ── Command parser ────────────────────────────────────────────────────────────

/*
 * processCommand()
 * Parses a null-terminated command string and acts on it.
 *
 * Supported commands:
 *   C<ch> <angle>  – set servo channel <ch> to <angle> degrees
 *   V              – print firmware version string
 */
void processCommand(const char* cmd) {
    // Version query
    if (cmd[0] == 'V' || cmd[0] == 'v') {
        Serial.println(F("servo_bridge v1.0"));
        return;
    }

    // Servo set command: "C<channel> <angle>"
    if (cmd[0] == 'C' || cmd[0] == 'c') {
        int channel = -1;
        int angle   = -1;

        // sscanf parses "C%d %d" — reads the integers after the 'C'
        int parsed = sscanf(cmd + 1, "%d %d", &channel, &angle);

        if (parsed != 2) {
            Serial.println(F("ERR"));
            return;
        }

        // Validate ranges
        if (channel < 0 || channel >= NUM_SERVOS) {
            Serial.println(F("ERR"));
            return;
        }
        if (angle < 0 || angle > 180) {
            Serial.println(F("ERR"));
            return;
        }

        // Write the angle to the servo
        // STEM note: Servo.write() converts degrees to a microsecond pulse
        // using the min/max values we set in attach().
        servos[channel].write(angle);

        Serial.println(F("OK"));
        return;
    }

    // Unknown command
    Serial.println(F("ERR"));
}
