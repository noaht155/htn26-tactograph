/* Gantry stepper (TMC2209 via STEP/DIR/EN, no UART config - current
 * from the driver's onboard Vref trimpot, microstepping from its
 * MS1/MS2 pull resistors). */
#ifndef STEPPER_H
#define STEPPER_H

#include <Arduino.h>

void stepperInit();

// Relative move by `steps` (+/- for direction). Non-blocking - call
// stepperUpdate() every loop() iteration until stepperIsMoving() is
// false.
void stepperMove(long steps);

// Decelerate and stop as soon as possible.
void stepperStop();

// Must be called every loop() iteration. Advances the step generator
// and disables the driver once a move finishes.
void stepperUpdate();

bool stepperIsMoving();
long stepperPosition();

#endif
