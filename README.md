# pressingClicks  Legacy (Terminal Version)

> **Version 1.1 — February 2026**  

A terminal-based mouse click recorder and player. Record a sequence of left-click positions, save them as a routine, and replay them in a loop  all from the command line.

> **Looking for the current GUI version?** See the [`main`](https://github.com/mangobax/pressingClicks/tree/main) branch.

---

## Features

- Console-driven setup — no GUI required
- Left & right click recording (middle click to stop)
- **Click & drag support** — automatically detected from mouse movement
- Save and load routines as JSON files
- Configurable delay between clicks and interval between routine loops
- Optional loop limit (0 = infinite)
- Slight position randomisation for more natural playback
- Customisable play/pause and exit hotkeys
- **DPI-aware** — coordinates are accurate on high-DPI / scaled displays

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

### 1. Configure

On launch the program prompts for:

| Prompt | Description |
|---|---|
| **Delay between clicks (s)** | Pause between each click in the routine |
| **Interval between routines (s)** | Pause after completing one full loop |
| **Max routine loops** | How many times to repeat (0 = infinite) |
| **Start/Pause hotkey** | Key to toggle playback (e.g. `f8`) |
| **Exit hotkey** | Key to quit the program (e.g. `esc`) |

### 2. Record or Load

After configuring, choose to:

- **Load** an existing routine from a `.json` file by entering the filename.
- **Record** a new routine:
  1. The program starts listening for mouse clicks.
  2. **Left or right click** anywhere to record that position.
  3. **Click and drag** to record a drag — automatically detected when the cursor moves more than 5 px between press and release.
  4. **Middle click** to stop recording.
  5. Optionally save the routine to a `.json` file for reuse.

### 3. Play Back

- Press the configured **Start/Pause hotkey** (default `F12`) to start playback.
- The routine replays in a loop, pausing between each full pass by the configured interval.
- Press the hotkey again to pause.
- Press the configured **Exit hotkey** (default `Esc`) to quit.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `F12` (default) | Toggle play / pause |
| `Esc` (default) | Exit the program |
| Middle click | Stop recording |

---

## Routine JSON Format

Routines are saved as a JSON array of click and drag objects:

```json
[
  { "type": "click", "button": "left",  "x": 540, "y": 360 },
  { "type": "click", "button": "right", "x": 800, "y": 200 },
  { "type": "drag",  "button": "left",  "x": 100, "y": 200, "end_x": 400, "end_y": 200, "duration": 0.35 }
]
```

You can edit these files manually to adjust coordinates or timing.

---

## Known Limitations

- No GUI — all interaction is via the terminal
- No per-click timing capture — a single global delay is applied to all events

---

## Clone & Run

```bash
git clone --branch legacy https://github.com/mangobax/pressingClicks.git pressingClicks-legacy
cd pressingClicks-legacy
pip install pynput
python pressingClicks.py
```

---

## License

[![License: CC BY-NC 4.0](https://licensebuttons.net/l/by-nc/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc/4.0/)

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/) license.  
Free to share and adapt  **non-commercial use only**.
