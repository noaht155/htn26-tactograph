"""
Tactograph controller module for Python.

Provides functions to control the Tactograph ESP32 hardware via serial:
- set_heights(arr): sets heights for 11 servos (channels 0..10, 0.0 to 1.0 -> 0 to 180 deg) using calibration.json
- reset_heights(): sets all 11 heights to 0
- set_lock(x): sets friction plate servo (channel 11) from 0.0 (unlocked) to 1.0 (locked)
- advance_stepper(x): steps gantry forward (x=1) or backward (x=-1) by 100 steps
"""

import os
import json
import time
from typing import List, Sequence, Optional, Union
import serial
import serial.tools.list_ports

CALIBRATION_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")


class TactographController:
    """Controller for ESP32-based Tactograph gantry, servos, and friction plate lock."""

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        calibration_path: Optional[str] = None,
        timeout: float = 3.0,
    ):
        self.baudrate = baudrate
        self.timeout = timeout
        self.calibration_path = calibration_path or CALIBRATION_FILE_PATH
        self.calibration = self.load_calibration(self.calibration_path)
        self.port = port or self.auto_detect_port()
        self.ser: Optional[serial.Serial] = None
        self._STEPCOUNT = -330
        self.connect()

    @staticmethod
    def auto_detect_port() -> str:
        """Find the ESP32 USB serial device."""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "USB" in p.device or "ACM" in p.device:
                return p.device
        if os.path.exists("/dev/ttyUSB0"):
            return "/dev/ttyUSB0"
        raise RuntimeError("No serial port found. Connect ESP32 to USB.")

    @staticmethod
    def load_calibration(path: str) -> dict:
        """Load servo and friction plate calibration data from JSON."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Calibration file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def connect(self) -> None:
        """Open serial connection to the ESP32 and verify communication."""
        print(f"[Tactograph] Connecting to {self.port} at {self.baudrate} baud...")
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(1.5)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        # Verify handshake with PING
        resp = self._send_raw_command("PING")
        if resp != "PONG":
            self.ser.reset_input_buffer()
            pos = self._send_raw_command("POS")
            print(f"[Tactograph] Connected to ESP32. Current stepper position: {pos}")
        else:
            print("[Tactograph] Connected to ESP32 (PING -> PONG verified).")

    def close(self) -> None:
        """Close serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[Tactograph] Serial connection closed.")

    def _send_raw_command(self, cmd: str) -> str:
        """Send a newline-terminated command line and return first stripped response."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not open.")

        while self.ser.in_waiting > 0:
            self.ser.readline()

        line_to_send = (cmd.strip() + "\n").encode("utf-8")
        self.ser.write(line_to_send)
        self.ser.flush()

        start_time = time.time()
        while time.time() - start_time < self.timeout:
            raw = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw:
                continue
            if raw == "READY":
                continue
            return raw

        raise TimeoutError(f"Timed out waiting for response to command: '{cmd}'")

    def height_to_pulse(self, channel: int, height: float) -> int:
        """
        Convert a real height (0.0 to 1.0) to servo pulse width (us) using calibration.json.
        Maps 0.0-1.0 to 0-180 degrees, then calculates pulse microseconds.
        """
        h = max(0.0, min(1.0, float(height)))
        target_angle_deg = h * 180.0

        servos_cal = self.calibration.get("servos", {})
        ch_cal = servos_cal.get(str(channel))

        if ch_cal is None:
            p0 = 550
            p180 = 2500
            direction = 1
            offset_deg = 0.0
        else:
            p0 = ch_cal.get("pulse_us_0deg", 550)
            p180 = ch_cal.get("pulse_us_180deg", 2500)
            direction = ch_cal.get("direction", 1)
            offset_deg = float(ch_cal.get("offset_deg", 0.0))

        if direction == 1:
            eff_angle = target_angle_deg + offset_deg
        else:
            eff_angle = 180.0 - (target_angle_deg + offset_deg)

        eff_angle = max(0.0, min(180.0, eff_angle))
        fraction = eff_angle / 180.0
        pulse_us = p0 + fraction * (p180 - p0)

        min_pulse = min(p0, p180)
        max_pulse = max(p0, p180)
        pulse_us = max(min_pulse, min(max_pulse, pulse_us))

        return int(round(pulse_us))

    def set_heights(self, arr: Sequence[Union[float, int]]) -> List[int]:
        """
        Sets heights for 11 servos (channels 0..10 inclusive).
        Each element is a real in [0.0, 1.0] that sets the height as an angle from 0 to 180 deg.
        Returns the list of pulse widths (microseconds) sent to the servos.
        """
        if len(arr) < 11:
            raise ValueError(f"set_heights expects an array of 11 reals (got {len(arr)})")

        pulses = [self.height_to_pulse(i, arr[i]) for i in range(11)]
        cmd = "SERVOS " + " ".join(str(p) for p in pulses)
        resp = self._send_raw_command(cmd)
        if resp != "OK":
            raise RuntimeError(f"Error from ESP32 on set_heights: {resp}")

        return pulses

    def reset_heights(self) -> List[int]:
        """
        Sets all 11 heights to 0 (0 degrees, retracted).
        Returns the list of pulse widths sent.
        """
        return self.set_heights([0.0] * 11)

    def set_lock(self, x: float) -> int:
        """
        Sets angle of channel 11 friction-plate servo:
        x = 0 -> unlocked_pulse_us (1500 us)
        x = 1 -> locked_pulse_us (900 us)
        Returns the pulse width (microseconds) set.
        """
        val = max(0.0, min(1.0, float(x)))
        mg_cfg = self.calibration.get("mg996r_friction_plate", {})
        channel = mg_cfg.get("channel", 11)
        unlocked_us = mg_cfg.get("unlocked_pulse_us", 1500)
        locked_us = mg_cfg.get("locked_pulse_us", 900)

        pulse_us = unlocked_us + val * (locked_us - unlocked_us)
        min_p = min(unlocked_us, locked_us)
        max_p = max(unlocked_us, locked_us)
        pulse_us = max(min_p, min(max_p, pulse_us))
        target_pulse = int(round(pulse_us))

        cmd = f"SERVO {channel} {target_pulse}"
        resp = self._send_raw_command(cmd)
        if resp != "OK":
            raise RuntimeError(f"Error setting lock servo: {resp}")

        return target_pulse

    def advance_stepper(self, x: int = 1) -> int:
        """
        Steps stepper forward (x=1) or backward (x=-1) by 100 steps.
        Waits for completion and returns the final stepper position.
        """
        if x not in (1, -1):
            steps = self._STEPCOUNT if x >= 0 else -self._STEPCOUNT
        else:
            steps = self._STEPCOUNT if x == 1 else -self._STEPCOUNT

        cmd = f"MOVE {steps}"
        resp = self._send_raw_command(cmd)
        if resp != "OK":
            raise RuntimeError(f"Error starting stepper move: {resp}")

        # Wait for "DONE <position>" from ESP32
        start_time = time.time()
        move_timeout = 10.0
        while time.time() - start_time < move_timeout:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("DONE "):
                return int(line.split()[1])

        raise TimeoutError(f"Timed out waiting for stepper move to complete ({cmd})")

    def get_position(self) -> int:
        """Get current stepper position."""
        resp = self._send_raw_command("POS")
        if resp.startswith("POS "):
            return int(resp.split()[1])
        raise RuntimeError(f"Unexpected response to POS: {resp}")

    def stop_stepper(self) -> None:
        """Immediately decelerate and stop the stepper."""
        resp = self._send_raw_command("STOP")
        if resp != "OK":
            raise RuntimeError(f"Error stopping stepper: {resp}")


# Global controller instance for convenient direct function calls
_default_controller: Optional[TactographController] = None


def get_controller(port: Optional[str] = None) -> TactographController:
    """Obtain or initialize the global controller instance."""
    global _default_controller
    if _default_controller is None:
        _default_controller = TactographController(port=port)
    return _default_controller


def set_heights(arr: Sequence[Union[float, int]]) -> List[int]:
    """
    Sets the heights for an array of 11 reals (0.0 to 1.0, channels 0..10 inclusive),
    mapping each height to an angle from 0 to 180 degrees using calibration.json.
    """
    return get_controller().set_heights(arr)


def reset_heights() -> List[int]:
    """Sets all 11 pin heights to 0."""
    return get_controller().reset_heights()


def set_lock(x: float) -> int:
    """
    Sets friction plate lock:
    x = 0.0 -> unlocked pulse us (channel 11)
    x = 1.0 -> locked pulse us (channel 11)
    """
    return get_controller().set_lock(x)


def advance_stepper(x: int = 1) -> int:
    """
    Steps gantry stepper forward (x=1) or backward (x=-1) by 100 steps.
    """
    return get_controller().advance_stepper(x)
