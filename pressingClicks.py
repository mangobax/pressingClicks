"""
Title: pressingClicks
Description: Advanced Click Recorder & Player with GUI
Author: MANGOBA
Version: 28-Feb-2026

Features:
- Tkinter GUI interface
- Save / Load routines (JSON)
- Left & Right click support
- Click & drag support (auto-detected)
- Customizable hotkeys
- Routine loop limit
- Adjustable randomness strength
- Per-click delay (real-time timing capture)
- Macro timeline with live recording feed
"""

import sys
import json
import threading
import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from time import sleep, time
from random import uniform
from pynput.mouse import Controller, Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener

# ==============================
# DPI Awareness (Windows)
# Must be called before any window creation or mouse listener starts so that
# all coordinate spaces (recording, playback, Tkinter) use physical pixels.
# ==============================
if sys.platform == "win32":
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2  (best option, Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback for Windows Vista/7/8
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ==============================
# Defaults
# ==============================
DEFAULT_DELAY = 1.0
DEFAULT_INTERVAL = 5.0
DEFAULT_FILENAME = "click_routine.json"
DEFAULT_RANDOMNESS = 0.3   # 0.0 = none, 1.0 = maximum
DRAG_THRESHOLD_PX = 5      # pixels of movement to distinguish drag from click


# ==============================
# Utility
# ==============================
def randomize(value, strength=DEFAULT_RANDOMNESS):
    """Apply randomness to a numeric value scaled by strength (0.0–1.0)."""
    if strength == 0:
        return value
    if isinstance(value, float):
        delta = value * strength * 0.5
        return value + uniform(-delta, delta)
    if isinstance(value, int):
        delta = max(1, int(abs(value) * strength * 0.1))
        return value + int(uniform(-delta, delta))
    return value


def parse_hotkey(user_input, default):
    """Convert a string like 'f8' or 'esc' to a pynput Key object."""
    try:
        s = user_input.strip().lower()
        if hasattr(Key, s):
            return getattr(Key, s)
        if len(s) == 1:
            return s
    except Exception:
        pass
    return default


# ==============================
# Click / Drag Player Thread
# ==============================
class ClickPlayer(threading.Thread):
    def __init__(self, config_getter, events_getter, status_cb=None):
        super().__init__(daemon=True)
        self.mouse = Controller()
        self.config_getter = config_getter   # callable → dict
        self.events_getter = events_getter   # callable → list
        self._running = threading.Event()
        self._alive = True
        self.loop_count = 0
        self.status_cb = status_cb or (lambda msg: None)

    # --- event performers ---

    def _pre_delay(self, event, strength):
        """Wait for the per-event delay.
        'recorded' mode uses the captured inter-event timing (falls back to
        the global setting if no timing was stored).
        'settings' mode always uses the global Click Delay value.
        """
        cfg = self.config_getter()
        if cfg.get("delay_mode", "recorded") == "settings":
            raw = cfg["delay"]
        else:
            raw = event.get("delay", cfg["delay"])
        sleep(max(0.0, randomize(float(raw), strength)))

    def perform_click(self, event, strength):
        self._pre_delay(event, strength)
        x = int(randomize(event["x"], strength))
        y = int(randomize(event["y"], strength))
        button = Button.left if event.get("button", "left") == "left" else Button.right
        self.mouse.position = (x, y)
        self.mouse.press(button)
        sleep(uniform(0.05, 0.1 + strength * 0.2))
        self.mouse.release(button)

    def perform_drag(self, event, strength):
        self._pre_delay(event, strength)
        x1 = int(randomize(event["x"], strength))
        y1 = int(randomize(event["y"], strength))
        x2 = int(randomize(event["end_x"], strength))
        y2 = int(randomize(event["end_y"], strength))
        button = Button.left if event.get("button", "left") == "left" else Button.right
        duration = max(0.05, float(event.get("duration", 0.3)))
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

    # --- thread loop ---

    def run(self):
        while self._alive:
            self._running.wait()
            cfg = self.config_getter()
            events = self.events_getter()
            strength = cfg.get("randomness", DEFAULT_RANDOMNESS)
            max_loops = cfg.get("max_loops", 0)

            if max_loops and self.loop_count >= max_loops:
                self.status_cb("Reached max loop limit.")
                self._running.clear()
                continue

            if not events:
                self._running.clear()
                self.status_cb("No events to play.")
                continue

            for event in events:
                if not self._running.is_set():
                    break
                if event.get("type", "click") == "drag":
                    self.perform_drag(event, strength)
                else:
                    self.perform_click(event, strength)

            self.loop_count += 1
            interval = cfg.get("interval", DEFAULT_INTERVAL)
            sleep(max(0.0, randomize(interval, strength)))

    # --- controls ---

    def start_clicking(self):
        self.status_cb("Playing")
        self._running.set()

    def stop_clicking(self):
        self.status_cb("Paused")
        self._running.clear()

    def toggle(self):
        if self._running.is_set():
            self.stop_clicking()
        else:
            self.start_clicking()

    def shutdown(self):
        self._alive = False
        self._running.set()


# ==============================
# Recorder
# ==============================
class Recorder:
    """
    Records mouse events with real-time inter-event timing.
    - Left / Right click → "click" event
    - Left / Right click + significant movement → "drag" event
    - stop_trigger: Button.middle (default) or a pynput Key / char that stops recording
    """

    def __init__(self, on_event_cb, on_done_cb, stop_trigger=None):
        self.on_event_cb = on_event_cb
        self.on_done_cb = on_done_cb
        self.stop_trigger = stop_trigger if stop_trigger is not None else Button.middle
        self.events = []
        self._press_info = {}
        self._last_event_time = None
        self._listener = None
        self._kb_listener = None

    def start(self):
        self.events = []
        self._press_info = {}
        self._last_event_time = time()
        self._listener = MouseListener(on_click=self._on_click)
        self._listener.start()
        # If the stop trigger is a keyboard key, also start a keyboard listener
        if self.stop_trigger is not Button.middle:
            def on_press(key):
                if key == self.stop_trigger:
                    self._stop_and_done()
                    return False
            self._kb_listener = KeyboardListener(on_press=on_press)
            self._kb_listener.daemon = True
            self._kb_listener.start()

    def _stop_and_done(self):
        if self._listener and self._listener.is_alive():
            self._listener.stop()
        if self._kb_listener and self._kb_listener.is_alive():
            self._kb_listener.stop()
        self.on_done_cb(self.events)

    def _on_click(self, x, y, button, pressed):
        if button == Button.middle and pressed and self.stop_trigger is Button.middle:
            self._stop_and_done()
            return False

        if button not in (Button.left, Button.right):
            return

        now = time()
        if pressed:
            self._press_info[button] = (x, y, now)
        else:
            if button not in self._press_info:
                return
            px, py, press_time = self._press_info.pop(button)
            delay = press_time - self._last_event_time
            self._last_event_time = now
            duration = now - press_time
            btn_str = "left" if button == Button.left else "right"
            dx, dy = abs(x - px), abs(y - py)

            if dx > DRAG_THRESHOLD_PX or dy > DRAG_THRESHOLD_PX:
                event = {
                    "type": "drag",
                    "button": btn_str,
                    "x": px, "y": py,
                    "end_x": x, "end_y": y,
                    "duration": round(duration, 3),
                    "delay": round(max(0.0, delay), 3),
                }
            else:
                event = {
                    "type": "click",
                    "button": btn_str,
                    "x": px, "y": py,
                    "delay": round(max(0.0, delay), 3),
                }

            self.events.append(event)
            self.on_event_cb(event)

    def stop(self):
        if self._listener and self._listener.is_alive():
            self._listener.stop()
        if self._kb_listener and self._kb_listener.is_alive():
            self._kb_listener.stop()


# ==============================
# GUI Application
# ==============================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("pressingClicks — Advanced Auto Clicker")
        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass  # icon not found — silently fall back to default
        self.resizable(False, False)

        self.events = []
        self.player = None
        self.recorder = None
        self.kb_listener = None

        self._build_ui()
        self._start_player()
        self._apply_hotkeys()          # load default hotkeys on startup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================
    # UI construction
    # =========================================================
    def _build_ui(self):
        PAD = {"padx": 8, "pady": 4}

        # ── Settings ─────────────────────────────────────────
        sf = ttk.LabelFrame(self, text="Settings")
        sf.grid(row=0, column=0, padx=10, pady=8, sticky="ew")

        # Delay
        ttk.Label(sf, text="Click Delay (s):").grid(row=0, column=0, sticky="w", **PAD)
        self.delay_var = tk.DoubleVar(value=DEFAULT_DELAY)
        ttk.Entry(sf, textvariable=self.delay_var, width=8).grid(row=0, column=1, **PAD)

        # Delay mode selector (row 1, left column — separate from hotkeys)
        ttk.Label(sf, text="Delay Mode:").grid(row=1, column=0, sticky="w", **PAD)
        self.delay_mode_var = tk.StringVar(value="recorded")
        mode_frame = ttk.Frame(sf)
        mode_frame.grid(row=1, column=1, sticky="w", **PAD)
        ttk.Radiobutton(mode_frame, text="Recorded",
                        variable=self.delay_mode_var,
                        value="recorded").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Settings",
                        variable=self.delay_mode_var,
                        value="settings").pack(side="left")

        # Interval
        ttk.Label(sf, text="Routine Interval (s):").grid(row=2, column=0, sticky="w", **PAD)
        self.interval_var = tk.DoubleVar(value=DEFAULT_INTERVAL)
        ttk.Entry(sf, textvariable=self.interval_var, width=8).grid(row=2, column=1, **PAD)

        # Max loops
        ttk.Label(sf, text="Max Loops (0=\u221e):").grid(row=3, column=0, sticky="w", **PAD)
        self.max_loops_var = tk.IntVar(value=0)
        ttk.Entry(sf, textvariable=self.max_loops_var, width=8).grid(row=3, column=1, **PAD)

        # Randomness strength
        ttk.Label(sf, text="Randomness:").grid(row=4, column=0, sticky="w", **PAD)
        self.randomness_var = tk.DoubleVar(value=DEFAULT_RANDOMNESS)
        rand_frame = ttk.Frame(sf)
        rand_frame.grid(row=4, column=1, **PAD)
        ttk.Scale(rand_frame, from_=0.0, to=1.0, orient="horizontal",
                  variable=self.randomness_var, length=100).pack(side="left")
        self.rand_label = ttk.Label(rand_frame,
                                    text=f"{DEFAULT_RANDOMNESS:.2f}", width=4)
        self.rand_label.pack(side="left")
        self.randomness_var.trace_add("write",
            lambda *_: self.rand_label.config(
                text=f"{self.randomness_var.get():.2f}"))

        # Hotkeys (right column — rows 0-2, no longer sharing row 0 with Delay Mode)
        ttk.Label(sf, text="Play/Pause Key:").grid(row=0, column=2, sticky="w", **PAD)
        self.start_key_var = tk.StringVar(value="f9")
        hk_frame0 = ttk.Frame(sf)
        hk_frame0.grid(row=0, column=3, sticky="w", **PAD)
        ttk.Entry(hk_frame0, textvariable=self.start_key_var, width=8).pack(side="left")
        self._cap_btn_start = ttk.Button(hk_frame0, text="⏺", width=2,
            command=lambda: self._start_key_capture(self.start_key_var, self._cap_btn_start))
        self._cap_btn_start.pack(side="left", padx=(2, 0))

        ttk.Label(sf, text="Stop Record Key:").grid(row=1, column=2, sticky="w", **PAD)
        self.stop_rec_key_var = tk.StringVar(value="middle")
        hk_frame2 = ttk.Frame(sf)
        hk_frame2.grid(row=1, column=3, sticky="w", **PAD)
        ttk.Entry(hk_frame2, textvariable=self.stop_rec_key_var, width=8).pack(side="left")
        self._cap_btn_stoprec = ttk.Button(hk_frame2, text="⏺", width=2,
            command=lambda: self._start_key_capture(self.stop_rec_key_var,
                                                    self._cap_btn_stoprec,
                                                    allow_mouse=True))
        self._cap_btn_stoprec.pack(side="left", padx=(2, 0))
        ttk.Label(sf, text="('middle' = middle click)",
                  foreground="gray").grid(row=2, column=2, columnspan=2,
                                          sticky="w", **PAD)

        ttk.Button(sf, text="Apply Hotkeys",
                   command=self._apply_hotkeys).grid(row=3, column=2,
                                                     columnspan=2, **PAD)

        # ── Controls ──────────────────────────────────────────
        cf = ttk.LabelFrame(self, text="Controls")
        cf.grid(row=1, column=0, padx=10, pady=4, sticky="ew")

        self.record_btn = ttk.Button(cf, text="\u23fa Record",
                                     command=self._toggle_record)
        self.record_btn.grid(row=0, column=0, **PAD)

        self.play_btn = ttk.Button(cf, text="\u25b6 Play",
                                   command=self._toggle_play)
        self.play_btn.grid(row=0, column=1, **PAD)

        ttk.Button(cf, text="Load Routine",
                   command=self._load_routine).grid(row=0, column=2, **PAD)
        ttk.Button(cf, text="Save Routine",
                   command=self._save_routine).grid(row=0, column=3, **PAD)
        ttk.Button(cf, text="Clear",
                   command=self._clear_events).grid(row=0, column=4, **PAD)

        self.on_top_var = tk.BooleanVar(value=False)
        self.on_top_btn = ttk.Checkbutton(
            cf, text="Always on Top",
            variable=self.on_top_var,
            command=self._toggle_always_on_top,
        )
        self.on_top_btn.grid(row=0, column=5, **PAD)

        # ── Status bar ────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var,
                  relief="sunken", anchor="w").grid(row=2, column=0,
                                                    padx=10, sticky="ew")

        # ── Macro Timeline ────────────────────────────────────
        tf = ttk.LabelFrame(self, text="Macro Timeline")
        tf.grid(row=3, column=0, padx=10, pady=8, sticky="nsew")

        cols = ("Index", "Type", "Button", "X", "Y",
                "End X", "End Y", "Delay (s)", "Duration (s)")
        col_widths = (50, 60, 60, 60, 60, 60, 60, 80, 90)

        self.timeline = ttk.Treeview(tf, columns=cols,
                                     show="headings", height=14)
        for col, w in zip(cols, col_widths):
            self.timeline.heading(col, text=col)
            self.timeline.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tf, orient="vertical",
                            command=self.timeline.yview)
        self.timeline.configure(yscrollcommand=vsb.set)
        self.timeline.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # right-click context menu for deletion
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Delete event",
                                   command=self._delete_selected_event)
        self.timeline.bind("<Button-3>", self._on_timeline_right_click)

    # =========================================================
    # Player
    # =========================================================
    def _get_config(self):
        try:    delay = float(self.delay_var.get())
        except Exception: delay = DEFAULT_DELAY
        try:    interval = float(self.interval_var.get())
        except Exception: interval = DEFAULT_INTERVAL
        try:    max_loops = int(self.max_loops_var.get())
        except Exception: max_loops = 0
        return {
            "delay":      delay,
            "interval":   interval,
            "max_loops":  max_loops,
            "randomness": self.randomness_var.get(),
            "delay_mode": self.delay_mode_var.get(),
        }

    def _get_events(self):
        return self.events

    def _start_player(self):
        self.player = ClickPlayer(
            config_getter=self._get_config,
            events_getter=self._get_events,
            status_cb=self._set_status,
        )
        self.player.start()

    def _toggle_play(self):
        if self.recorder and self.recorder._listener \
                and self.recorder._listener.is_alive():
            messagebox.showwarning("Recording", "Stop recording before playing.")
            return
        if not self.events:
            messagebox.showwarning("No Events",
                                   "Record or load a routine first.")
            return
        self.player.toggle()
        self._update_play_btn()

    def _update_play_btn(self):
        if self.player._running.is_set():
            self.play_btn.config(text="\u23f8 Pause")
        else:
            self.play_btn.config(text="\u25b6 Play")

    # =========================================================
    # Recorder
    # =========================================================
    def _toggle_record(self):
        recording = (self.recorder is not None
                     and self.recorder._listener is not None
                     and self.recorder._listener.is_alive())
        if recording:
            self.recorder.stop()
            self._finish_recording(self.recorder.events)
        else:
            if self.player._running.is_set():
                self.player.stop_clicking()
                self._update_play_btn()
            # clear previous data for a fresh recording
            self.events = []
            self._refresh_timeline()
            self._set_status("Recording…  Middle Click to stop.")
            self.record_btn.config(text="\u23f9 Stop Recording")
            self.recorder = Recorder(
                on_event_cb=self._on_record_event,
                on_done_cb=self._on_record_done,
                stop_trigger=self._parse_stop_rec_key(),
            )
            self.recorder.start()
            self.iconify()

    def _on_record_event(self, event):
        """Called from the listener thread — schedule UI update on main thread."""
        self.after(0, self._add_timeline_row, event,
                   len(self.recorder.events) - 1)

    def _on_record_done(self, events):
        self.after(0, self._finish_recording, events)

    def _finish_recording(self, events):
        self.events = list(events)
        self.record_btn.config(text="\u23fa Record")
        self._set_status(f"Recorded {len(events)} event(s).")
        self.deiconify()

    # =========================================================
    # Timeline helpers
    # =========================================================
    def _add_timeline_row(self, event, index):
        etype = event.get("type", "click")
        row = (
            index + 1,
            etype,
            event.get("button", ""),
            event.get("x", ""),
            event.get("y", ""),
            event.get("end_x", "-") if etype == "drag" else "-",
            event.get("end_y", "-") if etype == "drag" else "-",
            f"{event.get('delay', 0):.3f}",
            f"{event.get('duration', 0):.3f}" if etype == "drag" else "-",
        )
        self.timeline.insert("", "end", values=row)

    def _refresh_timeline(self):
        for item in self.timeline.get_children():
            self.timeline.delete(item)
        for i, event in enumerate(self.events):
            self._add_timeline_row(event, i)

    def _on_timeline_right_click(self, event):
        row = self.timeline.identify_row(event.y)
        if row:
            self.timeline.selection_set(row)
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _delete_selected_event(self):
        selected = self.timeline.selection()
        if not selected:
            return
        idx = self.timeline.index(selected[0])
        self.timeline.delete(selected[0])
        if 0 <= idx < len(self.events):
            del self.events[idx]
        self._refresh_timeline()

    def _clear_events(self):
        if messagebox.askyesno("Clear", "Clear all recorded events?"):
            self.events = []
            self._refresh_timeline()
            self._set_status("Cleared.")

    # =========================================================
    # Save / Load
    # =========================================================
    def _save_routine(self):
        if not self.events:
            messagebox.showwarning("Empty", "No events to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=DEFAULT_FILENAME,
        )
        if path:
            with open(path, "w") as f:
                json.dump(self.events, f, indent=4)
            self._set_status(f"Saved to {path}")

    def _load_routine(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # backward-compat: old format has no "type" field → treat as click
            for ev in data:
                ev.setdefault("type", "click")
            self.events = data
            self._refresh_timeline()
            self._set_status(f"Loaded {len(self.events)} event(s) from {path}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    # =========================================================
    # Hotkeys
    # =========================================================
    def _apply_hotkeys(self):
        if self.kb_listener:
            self.kb_listener.stop()

        start_key = parse_hotkey(self.start_key_var.get(), Key.f8)
        exit_key = Key.esc  # hardcoded — Esc always exits

        def on_press(key):
            if key == start_key:
                self.after(0, self._toggle_play)
            elif key == exit_key:
                self.after(0, self._on_close)

        self.kb_listener = KeyboardListener(on_press=on_press)
        self.kb_listener.daemon = True
        self.kb_listener.start()
        self._set_status(
            f"Hotkeys applied — {start_key} = Play/Pause | "
            f"Esc = Exit | "
            f"{self.stop_rec_key_var.get()} = Stop Recording"
        )

    def _parse_stop_rec_key(self):
        """Return Button.middle for 'middle', otherwise a pynput Key/char."""
        raw = self.stop_rec_key_var.get().strip().lower()
        if raw == "middle":
            return Button.middle
        return parse_hotkey(raw, Button.middle)

    def _start_key_capture(self, target_var, btn, allow_mouse=False):
        """Wait for the next keypress (or middle-click when allow_mouse=True)
        and write its name into target_var."""
        original_text = btn.cget("text")
        btn.config(text="...", state="disabled")
        self._set_status("Press the desired key now…")

        def finish(name):
            target_var.set(name)
            self.after(0, lambda: btn.config(text=original_text, state="normal"))
            self._set_status(f"Key set to: {name}")

        def on_key(key):
            try:
                name = key.name          # special key, e.g. 'f8', 'esc'
            except AttributeError:
                name = key.char or str(key)   # regular character
            self.after(0, finish, name)
            return False                 # stop listener

        kb = KeyboardListener(on_press=on_key)
        kb.daemon = True

        if allow_mouse:
            def on_mouse_click(x, y, button, pressed):
                if pressed and button == Button.middle:
                    kb.stop()
                    self.after(0, finish, "middle")
                    return False
            mouse_l = MouseListener(on_click=on_mouse_click)
            mouse_l.daemon = True
            mouse_l.start()
            # patch kb stop to also stop mouse listener
            _orig_stop = kb.stop
            def _patched_stop():
                _orig_stop()
                if mouse_l.is_alive():
                    mouse_l.stop()
            kb.stop = _patched_stop

        kb.start()

    # =========================================================
    # Misc
    # =========================================================
    def _set_status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _toggle_always_on_top(self):
        self.attributes("-topmost", self.on_top_var.get())

    def _on_close(self):
        if self.player:
            self.player.shutdown()
        if self.recorder:
            self.recorder.stop()
        if self.kb_listener:
            self.kb_listener.stop()
        self.destroy()


# ==============================
# Entry Point
# ==============================
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)