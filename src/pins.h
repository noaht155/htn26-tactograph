/* Pin mapping for the ESP32 gantry+servo controller. Confirmed working
 * on real hardware (see CHANGELOG.md). */
#ifndef PINS_H
#define PINS_H

// TMC2209 stepper driver (STEP/DIR/EN only, no UART config)
#define STEPPER_EN_PIN 25
#define STEPPER_STEP_PIN 13
#define STEPPER_DIR_PIN 14

// PCA9685 servo driver, I2C
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define PCA9685_ADDR 0x40

#endif
