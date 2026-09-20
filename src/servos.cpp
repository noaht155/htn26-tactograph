#include "servos.h"
#include "pins.h"
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// 50Hz (20ms period) to match the pulse_us <-> count math already
// documented in CLAUDE.md's "Servo calibration" section - Adafruit's
// writeMicroseconds() is frequency-aware, but keeping this consistent
// with the rest of the project avoids confusion.
static const uint16_t PWM_FREQ_HZ = 50;

static Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(PCA9685_ADDR);

void servosInit()
{
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    pwm.begin();
    pwm.setPWMFreq(PWM_FREQ_HZ);
    delay(10);
}

void servoSetPulseUs(uint8_t channel, uint16_t pulseUs)
{
    pwm.writeMicroseconds(channel, pulseUs);
}

void servoSetAllPulseUs(uint8_t count, uint16_t pulseUs)
{
    for (uint8_t ch = 0; ch < count; ch++)
    {
        pwm.writeMicroseconds(ch, pulseUs);
    }
}

void servoSetMultiplePulseUs(uint8_t startChannel, uint8_t count, const uint16_t *pulseUs)
{
    for (uint8_t i = 0; i < count; i++)
    {
        uint8_t ch = startChannel + i;
        if (ch < NUM_SERVO_CHANNELS)
        {
            pwm.writeMicroseconds(ch, pulseUs[i]);
        }
    }
}

void servoOff(uint8_t channel)
{
    pwm.setPWM(channel, 0, 4096); // full-off bit, see PCA9685 datasheet
}
