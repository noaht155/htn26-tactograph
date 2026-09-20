/* PCA9685-driven servos: 11x SG90 (print head) + 1x MG996R (friction
 * plate), per CLAUDE.md. This module only sets raw pulse widths - angle/
 * height calibration math stays on the Pi (calibration.json), matching
 * the project's "keep the planner as pure functions" split. */
#ifndef SERVOS_H
#define SERVOS_H

#include <Arduino.h>

#define NUM_SERVO_CHANNELS 16 // PCA9685 has 16 channels total

void servosInit();

// Set one channel's pulse width directly in microseconds.
void servoSetPulseUs(uint8_t channel, uint16_t pulseUs);

// Set every channel from 0..count-1 to the same pulse width. Mainly for
// bring-up/testing, not the real per-row planner.
void servoSetAllPulseUs(uint8_t count, uint16_t pulseUs);

// Set multiple consecutive channels starting at startChannel.
void servoSetMultiplePulseUs(uint8_t startChannel, uint8_t count, const uint16_t *pulseUs);

// Fully release a channel (no signal).
void servoOff(uint8_t channel);

#endif
