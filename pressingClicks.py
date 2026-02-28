"""
Title: pressingClicks
Description: Legacy Click Recorder & Player
Author: MANGOBA
Version: 28-Feb-2026

Features:
- Save / Load routines (JSON)
- Left & Right click support
- Click & drag support (auto-detected)
- Customizable hotkeys
- Routine loop limit
- DPI-aware coordinate recording
"""

import sys
import json
import ctypes
import threading
from time import sleep, time
from random import uniform
from pynput.mouse import Controller, Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener

# ==============================
# DPI Awareness (Windows)
# ==============================
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ==============================
# Defaults
# ==============================
DEFAULT_DELAY = 1.0
DEFAULT_INTERVAL = 5.0
DEFAULT_FILENAME = "click_routine.json"


# ==============================
# Utility
# ==============================
def randomize(value):
    if isinstance(value, float):
        return uniform(value - 0.2, value + 0.2)
    if isinstance(value, int):
        return uniform(value - 2, value + 2)
    return value


def get_float(prompt, default):
    try:
        return float(input(prompt))
    except ValueError:
        print(f"Invalid input. Using default: {default}")
        return default


def get_int(prompt, default):
    try:
        return int(input(prompt))
    except ValueError:
        print(f"Invalid input. Using default: {default}")
        return default


def parse_hotkey(user_input, default):
    """
    Convert user string to pynput Key
    Example: f8 -> Key.f8
             esc -> Key.esc
    """
    try:
        if hasattr(Key, user_input.lower()):
            return getattr(Key, user_input.lower())
        elif len(user_input) == 1:
            return user_input.lower()
    except Exception:
        pass

    print(f"Invalid hotkey. Using default: {default}")
    return default


# ==============================
# Click Player Thread
# ==============================
class ClickPlayer(threading.Thread):
    def __init__(self, delay, interval, clicks, max_loops):
        super().__init__(daemon=True)
        self.mouse = Controller()
        self.delay = delay
        self.interval = interval
        self.clicks = clicks
        self.max_loops = max_loops

        self._running = threading.Event()
        self._alive = True
        self.loop_count = 0

    def perform_click(self, click_data):
        x = int(randomize(click_data["x"]))
        y = int(randomize(click_data["y"]))
        button = Button.left if click_data["button"] == "left" else Button.right

        self.mouse.position = (x, y)
        self.mouse.press(button)
        sleep(uniform(0.1, 0.3))
        self.mouse.release(button)

        sleep(randomize(self.delay))

    def perform_drag(self, click_data):
        x1 = int(randomize(click_data["x"]))
        y1 = int(randomize(click_data["y"]))
        x2 = int(randomize(click_data["end_x"]))
        y2 = int(randomize(click_data["end_y"]))
        button = Button.left if click_data["button"] == "left" else Button.right
        duration = float(click_data.get("duration", 0.3))
        steps = max(10, int(duration * 60))

        self.mouse.position = (x1, y1)
        self.mouse.press(button)
        for i in range(steps + 1):
            if not self._running.is_set():
                break
            t = i / steps
            self.mouse.position = (int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t))
            sleep(duration / steps)
        self.mouse.release(button)

        sleep(randomize(self.delay))

    def run(self):
        while self._alive:
            self._running.wait()

            if self.max_loops and self.loop_count >= self.max_loops:
                print("Reached max loop limit.")
                self._running.clear()
                continue

            for click in self.clicks:
                if not self._running.is_set():
                    break
                if click.get("type") == "drag":
                    self.perform_drag(click)
                else:
                    self.perform_click(click)

            self.loop_count += 1
            sleep(randomize(self.interval))

    def start_clicking(self):
        print("▶ Playing")
        self._running.set()

    def stop_clicking(self):
        print("⏸ Paused")
        self._running.clear()

    def shutdown(self):
        self._alive = False
        self._running.set()


# ==============================
# Recording
# ==============================
DRAG_THRESHOLD_PX = 5

def record_clicks():
    recorded = []
    press_info = {}  # Button -> (x, y, timestamp)

    def on_click(x, y, button, pressed):
        if button == Button.middle and pressed:
            print("Recording stopped.")
            return False

        if button not in (Button.left, Button.right):
            return

        btn_str = "left" if button == Button.left else "right"

        if pressed:
            press_info[button] = (x, y, time())
        else:
            if button not in press_info:
                return
            px, py, press_time = press_info.pop(button)
            duration = time() - press_time
            dx, dy = abs(x - px), abs(y - py)

            if dx > DRAG_THRESHOLD_PX or dy > DRAG_THRESHOLD_PX:
                print(f"Recorded {btn_str} drag ({px},{py}) -> ({x},{y})")
                recorded.append({
                    "type": "drag",
                    "button": btn_str,
                    "x": px, "y": py,
                    "end_x": x, "end_y": y,
                    "duration": round(duration, 3),
                })
            else:
                print(f"Recorded {btn_str} click at ({px}, {py})")
                recorded.append({
                    "type": "click",
                    "button": btn_str,
                    "x": px, "y": py,
                })

    print("Recording clicks...")
    print("Left/Right Click = Record | Drag = Record drag | Middle Click = Stop")

    with MouseListener(on_click=on_click) as listener:
        listener.join()

    return recorded


# ==============================
# Save / Load
# ==============================
def save_routine(clicks, filename):
    with open(filename, "w") as f:
        json.dump(clicks, f, indent=4)
    print(f"Routine saved to {filename}")


def load_routine(filename):
    try:
        with open(filename, "r") as f:
            clicks = json.load(f)
        print(f"Loaded routine from {filename}")
        return clicks
    except FileNotFoundError:
        print("File not found.")
        return []


# ==============================
# Keyboard Controls
# ==============================
def keyboard_controls(player, start_key, exit_key):
    def on_press(key):
        if key == start_key:
            if player._running.is_set():
                player.stop_clicking()
            else:
                player.start_clicking()

        elif key == exit_key:
            print("Exiting program.")
            player.shutdown()
            return False

    print(f"{start_key} = Play/Pause | {exit_key} = Exit")

    with KeyboardListener(on_press=on_press) as listener:
        listener.join()


# ==============================
# Main
# ==============================
def main():
    while True:
        print("\n--- Advanced Auto Clicker ---")

        delay = get_float("Delay between clicks (seconds): ", DEFAULT_DELAY)
        interval = get_float("Interval between routines (seconds): ", DEFAULT_INTERVAL)
        max_loops = get_int("Max routine loops (0 = infinite): ", 0)

        start_key_input = input("Start/Pause hotkey (example: f8): ")
        exit_key_input = input("Exit hotkey (example: esc): ")

        start_key = parse_hotkey(start_key_input, Key.f12)
        exit_key = parse_hotkey(exit_key_input, Key.esc)

        choice = input("Load existing routine? (y/n): ").lower()

        if choice == "y":
            filename = input(f"Filename ({DEFAULT_FILENAME}): ") or DEFAULT_FILENAME
            clicks = load_routine(filename)
        else:
            clicks = record_clicks()
            save_choice = input("Save this routine? (y/n): ").lower()
            if save_choice == "y":
                filename = input(f"Filename ({DEFAULT_FILENAME}): ") or DEFAULT_FILENAME
                save_routine(clicks, filename)

        if not clicks:
            print("No clicks available. Restarting...\n")
            continue

        player = ClickPlayer(delay, interval, clicks, max_loops)
        player.start()

        keyboard_controls(player, start_key, exit_key)

        print("Restarting...\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)