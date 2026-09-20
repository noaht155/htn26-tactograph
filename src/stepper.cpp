#include "stepper.h"
#include "pins.h"
#include <AccelStepper.h>

// Conservative starting values - matches the slow/cautious speeds used
// during the Pi-side GPIO bring-up before this moved to the ESP32.
// Tune once the mechanism is under load.
static const float MAX_SPEED_STEPS_PER_S = 2000.0;
static const float ACCEL_STEPS_PER_S2 = 1000.0;

static AccelStepper stepper(AccelStepper::DRIVER, STEPPER_STEP_PIN, STEPPER_DIR_PIN);
static bool moving = false;

static void enableDriver()
{
    digitalWrite(STEPPER_EN_PIN, LOW); // active-low
}

static void disableDriver()
{
    digitalWrite(STEPPER_EN_PIN, HIGH);
}

void stepperInit()
{
    pinMode(STEPPER_EN_PIN, OUTPUT);
    disableDriver();

    stepper.setMaxSpeed(MAX_SPEED_STEPS_PER_S);
    stepper.setAcceleration(ACCEL_STEPS_PER_S2);
}

void stepperMove(long steps)
{
    enableDriver();
    stepper.move(steps);
    moving = true;
}

void stepperStop()
{
    stepper.stop();
}

void stepperUpdate()
{
    if (!moving)
    {
        return;
    }

    stepper.run();
    if (stepper.distanceToGo() == 0)
    {
        moving = false;
        disableDriver();
    }
}

bool stepperIsMoving()
{
    return moving;
}

long stepperPosition()
{
    return stepper.currentPosition();
}
