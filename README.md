# pressingClicks

A GUI-based mouse macro recorder and player. Record sequences of clicks and drags, save them as reusable routines, and play them back with human-like randomisation.

> **Looking for the original terminal version?** See the [`legacy`](https://github.com/mangobax/pressingClicks/tree/legacy) branch.

---

## Features

- **Tkinter GUI**  no terminal interaction required
- **Click & drag recording**  automatically detects drags based on cursor movement
- **Real-time timing capture**  inter-event delays are recorded as you perform them
- **Per-event delay control**  choose between recorded timings or a fixed settings delay
- **Adjustable randomness**  slider from 0 (exact) to 1 (maximum jitter) on position and timing
- **Left & right click support**
- **Save / Load routines** as JSON files
- **Macro timeline**  live-updating table showing every recorded event; right-click to delete individual rows
- **Customisable hotkeys**  set play/pause and stop-recording keys by typing or pressing the key directly
- **Always on Top** toggle
- **DPI-aware**  coordinates are accurate on high-DPI / scaled displays

---

## Requirements

- Python 3.8+
- [`pynput`](https://pypi.org/project/pynput/)

Install the dependency:

```bash
pip install pynput
```

---

## Running

```bash
python pressingClicks.py
```

---

## How to Use

### 1. Configure Settings

| Field | Description |
|---|---|
| **Click Delay (s)** | Fallback delay between clicks when using *Settings* delay mode |
| **Delay Mode** | *Recorded* uses captured timings; *Settings* uses the fixed delay above |
| **Routine Interval (s)** | Wait between full routine loops |
| **Max Loops** | Number of times to repeat the routine (0 = infinite) |
| **Randomness** | Slider controlling position and timing jitter (0 = none, 1 = max) |
| **Play/Pause Key** | Keyboard hotkey to start or pause playback |
| **Stop Record Key** | Key (or `middle` for middle mouse click) to stop recording |

Click **Apply Hotkeys** after changing any hotkey. Use the **** button next to a field to capture a key by pressing it directly.

### 2. Record a Routine

1. Click ** Record**  the window minimises automatically.
2. Perform your clicks and drags on screen. Each action is captured with its real timing.
3. Stop recording by pressing the configured **Stop Record Key** (default: middle mouse click). The window restores and the timeline fills in.

> **Drag detection:** if the cursor moves more than 5 px between press and release, the event is recorded as a drag with a start point, end point, and duration.

### 3. Review the Timeline

The **Macro Timeline** table shows every recorded event:

| Column | Meaning |
|---|---|
| Index | Order of execution |
| Type | `click` or `drag` |
| Button | `left` or `right` |
| X / Y | Start coordinates |
| End X / End Y | End coordinates (drags only) |
| Delay (s) | Time waited before this event |
| Duration (s) | How long the button was held (drags only) |

Right-click any row to delete it. Click **Clear** to remove all events.

### 4. Play Back

- Click ** Play** or press the configured play/pause hotkey.
- The routine loops according to **Max Loops** (0 = forever).
- Press the hotkey again or click ** Pause** to pause.
- Press **Esc** at any time to close the program.

### 5. Save & Load Routines

- **Save Routine**  exports the current event list to a `.json` file.
- **Load Routine**  imports a previously saved `.json` file. Old routines recorded with version 1 are backwards-compatible.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| Configured play/pause key (default `f9`) | Toggle play / pause |
| Configured stop-record key (default middle click) | Stop recording |
| `Esc` | Exit the program |

---

## Routine JSON Format

Routines are plain JSON arrays. Each event is an object:

```json
[
  { "type": "click", "button": "left",  "x": 540, "y": 360, "delay": 0.412 },
  { "type": "drag",  "button": "left",  "x": 100, "y": 200,
    "end_x": 400, "end_y": 200, "duration": 0.35, "delay": 0.8 }
]
```

You can edit these files manually to fine-tune timings or coordinates.

---

## Clone & Run

```bash
git clone https://github.com/mangobax/pressingClicks.git
cd pressingClicks
pip install pynput
python pressingClicks.py
```

---

## Legacy Version (terminal)

The original terminal-based version is preserved in the [`legacy`](https://github.com/mangobax/pressingClicks/tree/legacy) branch. It has no GUI — all configuration is done via console prompts.

```bash
git clone --branch legacy https://github.com/mangobax/pressingClicks.git pressingClicks-legacy
cd pressingClicks-legacy
pip install pynput
python pressingClicks.py
```

**Legacy features:**
- Console prompts for delay, interval, and loop count
- Left click recording only (middle click to stop)
- `F12` to play/pause, `Esc` to exit
- Save / load routines as JSON

---

## License

[![License: CC BY-NC 4.0](https://licensebuttons.net/l/by-nc/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc/4.0/)

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/) license.  
Free to share and adapt — **non-commercial use only**.
