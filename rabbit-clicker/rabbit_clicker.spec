from pathlib import Path

project_dir = Path(SPECPATH)

hiddenimports = [
    "pyautogui._pyautogui_win",
    "pynput._util.win32",
    "pynput._util.win32_vks",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
]

excludes = [
    "cv2",
    "numpy",
    "qtpy",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "mouseinfo",
    "pyautogui._pyautogui_java",
    "pyautogui._pyautogui_osx",
    "pyautogui._pyautogui_x11",
    "pynput._util.darwin",
    "pynput._util.darwin_vks",
    "pynput._util.uinput",
    "pynput._util.xorg",
    "pynput.keyboard._darwin",
    "pynput.keyboard._dummy",
    "pynput.keyboard._uinput",
    "pynput.keyboard._xorg",
    "pynput.mouse._darwin",
    "pynput.mouse._dummy",
    "pynput.mouse._xorg",
]


a = Analysis(
    [str(project_dir / "app.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="兔子点击器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(project_dir / "assets" / "rabbit_icon.ico"),
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
