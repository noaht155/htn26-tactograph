/* Tactograph gantry + servo controller (ESP32).
 *
 * Drives the TMC2209 stepper (STEP/DIR/EN only, no UART config) via
 * AccelStepper, and the PCA9685 servos (11x SG90 + 1x MG996R) over I2C,
 * both from commands sent by a Python script over USB serial as plain text lines.
 * See pins.h for wiring, stepper.h/servos.h for the per-subsystem API.
 *
 * Serial protocol (115200 baud, newline-terminated commands):
 *   MOVE <steps>              relative stepper move, +/- for direction.
 *                              Replies OK, then DONE <position> once the
 *                              move completes.
 *   ADVANCE_STEPPER <x>        step forward 100 steps (x >= 0) or back 100
 *                              steps (x < 0). Replies OK, then DONE <pos>.
 *   STOP                       decelerate and stop the stepper. Replies OK.
 *   POS                        reports stepper position. Replies POS <n>.
 *   HOME                       NOT IMPLEMENTED YET - StallGuard needs
 *                              TMC2209 UART config, intentionally
 *                              skipped (see CLAUDE.md). Replies
 *                              ERR HOME not implemented.
 *   SERVO <channel> <pulse_us> set one PCA9685 channel's pulse width
 *                              directly. Replies OK.
 *   SERVOS <p0> <p1> ...       set channels 0..N with space-separated pulse
 *                              widths in microseconds. Replies OK.
 *   SERVOALL <count> <pulse_us> set channels 0..count-1 to the same
 *                              pulse width. Replies OK.
 *   SERVOOFF <channel>         release one channel (no signal). Replies OK.
 *   SET_LOCK <pulse_us>        set friction plate servo (channel 11) pulse
 *                              width directly. Replies OK.
 *   RESET_HEIGHTS              set all print head servos (channels 0..10)
 *                              to 0 deg pulse (550us). Replies OK.
 *   PING                       health check. Replies PONG.
 *   Unknown command replies ERR unknown command: <text>
 */
#include <Arduino.h>
#include "pins.h"
#include "stepper.h"
#include "servos.h"

static String lineBuffer;

static void handleCommand(String line)
{
    line.trim();
    if (line.length() == 0)
    {
        return;
    }

    if (line.startsWith("MOVE "))
    {
        long steps = line.substring(5).toInt();
        stepperMove(steps);
        Serial.println("OK");
    }
    else if (line.startsWith("ADVANCE_STEPPER ") || line.startsWith("ADVANCE "))
    {
        int sep = line.indexOf(' ');
        int dir = line.substring(sep + 1).toInt();
        long steps = (dir >= 0) ? 100 : -100;
        stepperMove(steps);
        Serial.println("OK");
    }
    else if (line == "STOP")
    {
        stepperStop();
        Serial.println("OK");
    }
    else if (line == "POS")
    {
        Serial.print("POS ");
        Serial.println(stepperPosition());
    }
    else if (line == "HOME")
    {
        Serial.println("ERR HOME not implemented");
    }
    else if (line.startsWith("SET_LOCK "))
    {
        uint16_t pulseUs = (uint16_t)line.substring(9).toInt();
        servoSetPulseUs(11, pulseUs);
        Serial.println("OK");
    }
    else if (line == "RESET_HEIGHTS")
    {
        for (uint8_t ch = 0; ch < 11; ch++)
        {
            servoSetPulseUs(ch, 550);
        }
        Serial.println("OK");
    }
    else if (line.startsWith("SERVOS "))
    {
        uint16_t pulses[NUM_SERVO_CHANNELS];
        uint8_t count = 0;
        int idx = 7;
        while (idx < line.length() && count < NUM_SERVO_CHANNELS)
        {
            while (idx < line.length() && line.charAt(idx) == ' ')
            {
                idx++;
            }
            if (idx >= line.length())
            {
                break;
            }
            int nextSpace = line.indexOf(' ', idx);
            if (nextSpace < 0)
            {
                nextSpace = line.length();
            }
            pulses[count++] = (uint16_t)line.substring(idx, nextSpace).toInt();
            idx = nextSpace + 1;
        }
        servoSetMultiplePulseUs(0, count, pulses);
        Serial.println("OK");
    }
    else if (line.startsWith("SERVOALL "))
    {
        String rest = line.substring(9);
        int sep = rest.indexOf(' ');
        if (sep < 0)
        {
            Serial.print("ERR bad SERVOALL args: ");
            Serial.println(line);
            return;
        }
        uint8_t count = (uint8_t)rest.substring(0, sep).toInt();
        uint16_t pulseUs = (uint16_t)rest.substring(sep + 1).toInt();
        servoSetAllPulseUs(count, pulseUs);
        Serial.println("OK");
    }
    else if (line.startsWith("SERVOOFF "))
    {
        uint8_t channel = (uint8_t)line.substring(9).toInt();
        servoOff(channel);
        Serial.println("OK");
    }
    else if (line.startsWith("SERVO "))
    {
        String rest = line.substring(6);
        int sep = rest.indexOf(' ');
        if (sep < 0)
        {
            Serial.print("ERR bad SERVO args: ");
            Serial.println(line);
            return;
        }
        uint8_t channel = (uint8_t)rest.substring(0, sep).toInt();
        uint16_t pulseUs = (uint16_t)rest.substring(sep + 1).toInt();
        servoSetPulseUs(channel, pulseUs);
        Serial.println("OK");
    }
    else if (line == "PING")
    {
        Serial.println("PONG");
    }
    else
    {
        Serial.print("ERR unknown command: ");
        Serial.println(line);
    }
}

void setup()
{
    Serial.begin(115200);

    stepperInit();
    servosInit();

    Serial.println("READY");
}

void loop()
{
    while (Serial.available())
    {
        char c = (char)Serial.read();
        if (c == '\n')
        {
            handleCommand(lineBuffer);
            lineBuffer = "";
        }
        else if (c != '\r')
        {
            if (lineBuffer.length() < 256)
            {
                lineBuffer += c;
            }
        }
    }

    bool wasMoving = stepperIsMoving();
    stepperUpdate();
    if (wasMoving && !stepperIsMoving())
    {
        Serial.print("DONE ");
        Serial.println(stepperPosition());
    }
}
