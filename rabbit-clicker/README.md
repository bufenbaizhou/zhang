# 兔子点击器

This isolated project lives in the `rabbit-clicker` folder and builds the Windows desktop tool named `兔子点击器`. It uses a Chinese interface, supports a random wait range in seconds for each round, supports either a fixed number of rounds or continuous clicking, and lets you choose whether each round is a single click, double click, or triple click. The main window uses `tkinter`, mouse clicking uses `pyautogui`, and global hotkeys use `pynput`. When the app starts, a small floating box stays visible in the lower-right corner of the screen and shows the current status, target position, current mode, and counters.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Command

```bash
python app.py
```

Optional on Windows if you do not want a console window:

```bash
pythonw app.py
```

## Build EXE

```bash
build_exe.bat
```

After the build finishes, the clickable Windows app will be:

```text
dist\兔子点击器.exe
```

The build script also copies the same exe to the project root:

```text
兔子点击器.exe
```

## Hotkeys

- `Ctrl+Alt+K` starts the click loop.
- `Ctrl+Alt+L` stops the click loop.
- Use minimum and maximum wait values in seconds, such as `0.5` to `1.5`.
- Choose either continuous clicking or a fixed number of rounds.
- Choose whether each round is a single click, double click, or triple click.
- The round counter tracks executed cycles, while the actual click counter tracks physical clicks.
- The capture button minimizes the app, waits 3 seconds, captures the current mouse position, and starts clicking on the current top-layer window.

## Safety Notes

- `pyautogui.FAILSAFE` stays enabled at all times.
- Moving the cursor to a screen corner can trigger the PyAutoGUI fail-safe and stop the loop.
- The app validates the target coordinate before it starts clicking.
- The app rejects screen-corner targets because the corners are reserved for fail-safe behavior.
- The click loop runs on a background thread so the window stays responsive.
- A floating status box stays visible in the lower-right corner while the app is open.
- Double-click the floating box if you want to bring the main settings window to the front.
- Closing the app stops the click loop and shuts down the global hotkey listener.

## Limitations

- Python 3.10 or newer is required.
- Only fixed-coordinate clicking is supported.
- Random wait timing is supported, but only by using a simple user-defined minimum and maximum interval.
- No hidden or background clicking is implemented.
- No browser-specific or platform-specific automation is implemented.
- No image recognition, OCR, or networking is implemented.
- Multi-monitor layouts, negative coordinates, and high-DPI scaling depend on PyAutoGUI's coordinate model.
- This version is intended for Windows desktop use.
- Global hotkeys depend on operating system permissions and desktop environment support.
