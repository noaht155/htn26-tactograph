#!/usr/bin/env python3
"""
Main script to send commands to the Tactograph ESP32.

Functions available:
- set_heights([h0, h1, ..., h10]) # 11 reals 0.0 to 1.0 (maps to 0-180 deg)
- reset_heights()                 # sets all 11 heights to 0
- set_lock(x)                     # 0.0 = unlocked (1500us), 1.0 = locked (900us)
- advance_stepper(1)              # steps forward 100 steps
- advance_stepper(-1)             # steps backward 100 steps
"""

import time
from controller import (
    get_controller,
    set_heights,
    reset_heights,
    set_lock,
    advance_stepper,
)


def main():
    # Connects to ESP32 over serial (auto-detects /dev/ttyUSB0)
    ctrl = get_controller()

    print("Connected. Sending commands to ESP32...")

    # 1. Reset all 11 pin heights to 0
    print("Resetting heights...")
    reset_heights()
    time.sleep(0.5)

    set_lock(1)
    # # 2. Example: Set heights across all 11 pins (channels 0..10, values from 0.0 to 1.0)
    # print("Setting pin heights...")
    # sample_heights = [1.0] * 11
    # set_heights(sample_heights)
    # time.sleep(10.0)

    # # 3. Lock friction plate (channel 11: 0.0 = unlocked, 1.0 = locked)
    # print("Setting lock to 1.0 (locked)...")
    # set_lock(1.0)
    # time.sleep(3)

    # print("Setting lock to 0.0 (unlocked)...")
    # set_lock(0.0)
    # time.sleep(3)

    # # 4. Stepper motion: advance forward (+100 steps) then back (-100 steps)
    print("Advancing stepper forward by 100 steps (x=1)...")
    advance_stepper(1)
    advance_stepper(1)
    advance_stepper(1)
    time.sleep(0.5)

    print("Advancing stepper backward by 100 steps (x=-1)...")
    advance_stepper(-1)
    advance_stepper(-1)
    advance_stepper(-1)
    time.sleep(0.5)

    # 5. Reset heights to 0
    print("Resetting heights...")
    reset_heights()

    set_lock(0)
    print("Commands completed successfully.")
    ctrl.close()


if __name__ == "__main__":
    main()
