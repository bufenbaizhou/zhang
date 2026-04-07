from __future__ import annotations

import ctypes
import random
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Literal, cast

import pyautogui
from pynput import keyboard


MouseButton = Literal["left", "middle", "right"]
AppState = Literal["stopped", "running"]


@dataclass(frozen=True, slots=True)
class ClickConfig:
    x: int
    y: int
    min_wait_s: float
    max_wait_s: float
    button: MouseButton
    burst: int
    target_rounds: int | None

    def is_continuous(self) -> bool:
        return self.target_rounds is None

    def random_wait(self) -> float:
        return random.uniform(self.min_wait_s, self.max_wait_s)


class AutoClickerApp:
    BUTTON_LABELS: dict[str, MouseButton] = {
        "\u5de6\u952e": "left",
        "\u4e2d\u952e": "middle",
        "\u53f3\u952e": "right",
    }
    BUTTON_VALUES = {value: key for key, value in BUTTON_LABELS.items()}
    CLICK_STYLES: dict[str, int] = {
        "\u5355\u51fb": 1,
        "\u53cc\u51fb": 2,
        "\u4e09\u8fde\u51fb": 3,
    }
    CLICK_STYLE_VALUES = {value: key for key, value in CLICK_STYLES.items()}
    MODE_CONTINUOUS = "continuous"
    MODE_COUNT = "count"
    CAPTURE_START_DELAY_MS = 3000
    OVERLAY_WIDTH = 360
    OVERLAY_HEIGHT = 190
    OVERLAY_MARGIN = 16

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("\u5154\u5b50\u70b9\u51fb\u5668")
        self.root.geometry("800x610")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

        self.state: AppState = "stopped"
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.capture_start_job: str | None = None
        self.hotkey_listener: keyboard.GlobalHotKeys | None = None
        self.is_shutting_down = False
        self.active_config: ClickConfig | None = None

        self.round_count = 0
        self.physical_click_count = 0

        x, y = self._default_target_position()
        self.x_var = tk.StringVar(value=str(x))
        self.y_var = tk.StringVar(value=str(y))
        self.min_wait_var = tk.StringVar(value="0.5")
        self.max_wait_var = tk.StringVar(value="1.5")
        self.button_var = tk.StringVar(value="\u5de6\u952e")
        self.click_style_var = tk.StringVar(value="\u5355\u51fb")
        self.mode_var = tk.StringVar(value=self.MODE_CONTINUOUS)
        self.target_rounds_var = tk.StringVar(value="10")

        self.status_var = tk.StringVar(
            value="\u51c6\u5907\u5c31\u7eea\u3002\u8bbe\u7f6e\u540e\u6309 Ctrl+Alt+K \u5f00\u59cb\u3002"
        )
        self.round_count_var = tk.StringVar(value="0")
        self.physical_click_count_var = tk.StringVar(value="0")
        self.config_var = tk.StringVar(value="")
        self.overlay_state_var = tk.StringVar(value="\u5df2\u505c\u6b62")
        self.overlay_config_var = tk.StringVar(value="")
        self.overlay_counts_var = tk.StringVar(
            value="\u8f6e\u6b21\uff1a0 | \u5b9e\u9645\u70b9\u51fb\uff1a0"
        )

        self.entries: list[ttk.Entry] = []
        self.mode_radios: list[ttk.Radiobutton] = []
        self.button_combo: ttk.Combobox | None = None
        self.click_style_combo: ttk.Combobox | None = None
        self.target_rounds_entry: ttk.Entry | None = None
        self.capture_button: ttk.Button | None = None
        self.start_button: ttk.Button | None = None
        self.stop_button: ttk.Button | None = None
        self.overlay_window: tk.Toplevel | None = None
        self.overlay_state_label: tk.Label | None = None

        self._build_ui()
        self._build_overlay()
        self._bind_traces()
        self._refresh_config_summary()
        self._refresh_overlay()
        self._start_hotkeys()
        self._update_control_states()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="\u5154\u5b50\u70b9\u51fb\u5668\uff08\u4ec5\u7528\u4e8e\u672c\u5730\u754c\u9762\u6d4b\u8bd5\uff09",
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main,
            text=self._screen_text(),
            wraplength=740,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        config = ttk.LabelFrame(main, text="\u70b9\u51fb\u914d\u7f6e", padding=12)
        config.pack(fill="x")
        config.columnconfigure(1, weight=1)
        config.columnconfigure(3, weight=1)

        ttk.Label(config, text="\u76ee\u6807 X").grid(row=0, column=0, sticky="w", pady=4)
        x_entry = ttk.Entry(config, textvariable=self.x_var, width=14)
        x_entry.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 16))
        ttk.Label(config, text="\u76ee\u6807 Y").grid(row=0, column=2, sticky="w", pady=4)
        y_entry = ttk.Entry(config, textvariable=self.y_var, width=14)
        y_entry.grid(row=0, column=3, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(config, text="\u6700\u5c0f\u7b49\u5f85\uff08\u79d2\uff09").grid(row=1, column=0, sticky="w", pady=4)
        min_entry = ttk.Entry(config, textvariable=self.min_wait_var, width=14)
        min_entry.grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 16))
        ttk.Label(config, text="\u6700\u5927\u7b49\u5f85\uff08\u79d2\uff09").grid(row=1, column=2, sticky="w", pady=4)
        max_entry = ttk.Entry(config, textvariable=self.max_wait_var, width=14)
        max_entry.grid(row=1, column=3, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(config, text="\u9f20\u6807\u6309\u952e").grid(row=2, column=0, sticky="w", pady=4)
        self.button_combo = ttk.Combobox(
            config,
            textvariable=self.button_var,
            values=tuple(self.BUTTON_LABELS.keys()),
            state="readonly",
            width=12,
        )
        self.button_combo.grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 16))
        ttk.Label(config, text="\u6bcf\u8f6e\u70b9\u51fb").grid(row=2, column=2, sticky="w", pady=4)
        self.click_style_combo = ttk.Combobox(
            config,
            textvariable=self.click_style_var,
            values=tuple(self.CLICK_STYLES.keys()),
            state="readonly",
            width=12,
        )
        self.click_style_combo.grid(row=2, column=3, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(config, text="\u8fd0\u884c\u6a21\u5f0f").grid(row=3, column=0, sticky="w", pady=4)
        mode_frame = ttk.Frame(config)
        mode_frame.grid(row=3, column=1, sticky="w", pady=4, padx=(8, 16))
        radio1 = ttk.Radiobutton(
            mode_frame,
            text="\u6301\u7eed\u70b9\u51fb",
            variable=self.mode_var,
            value=self.MODE_CONTINUOUS,
        )
        radio1.pack(side="left")
        radio2 = ttk.Radiobutton(
            mode_frame,
            text="\u6307\u5b9a\u8f6e\u6b21",
            variable=self.mode_var,
            value=self.MODE_COUNT,
        )
        radio2.pack(side="left", padx=(14, 0))
        self.mode_radios = [radio1, radio2]

        ttk.Label(config, text="\u6267\u884c\u8f6e\u6b21").grid(row=3, column=2, sticky="w", pady=4)
        self.target_rounds_entry = ttk.Entry(config, textvariable=self.target_rounds_var, width=14)
        self.target_rounds_entry.grid(row=3, column=3, sticky="ew", pady=4, padx=(8, 0))
        ttk.Label(
            config,
            text="\u9009\u62e9\u201c\u6307\u5b9a\u8f6e\u6b21\u201d\u540e\u751f\u6548\uff0c\u8fbe\u5230\u540e\u81ea\u52a8\u505c\u6b62\u3002",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=4)

        self.capture_button = ttk.Button(
            config,
            text="\u6700\u5c0f\u5316\u540e 3 \u79d2\u6355\u83b7\u5e76\u5f00\u59cb",
            command=self.capture_current_position,
        )
        self.capture_button.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        self.entries = [x_entry, y_entry, min_entry, max_entry, self.target_rounds_entry]
        self._bind_entry_helpers(x_entry, y_entry, min_entry, max_entry, self.target_rounds_entry)

        controls = ttk.LabelFrame(main, text="\u63a7\u5236", padding=12)
        controls.pack(fill="x", pady=(12, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        self.start_button = ttk.Button(controls, text="\u5f00\u59cb\u8fde\u70b9", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_button = ttk.Button(controls, text="\u505c\u6b62\u8fde\u70b9", command=self.stop_clicking, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew")

        status = ttk.LabelFrame(main, text="\u72b6\u6001", padding=12)
        status.pack(fill="both", expand=True, pady=(12, 0))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="\u5f53\u524f\u72b6\u6001").grid(row=0, column=0, sticky="nw")
        ttk.Label(status, textvariable=self.status_var, wraplength=660, justify="left").grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
        )
        ttk.Label(status, text="\u5df2\u6267\u884c\u8f6e\u6b21").grid(row=1, column=0, sticky="w")
        ttk.Label(status, textvariable=self.round_count_var).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(0, 8))
        ttk.Label(status, text="\u5b9e\u9645\u70b9\u51fb\u6570").grid(row=2, column=0, sticky="w")
        ttk.Label(status, textvariable=self.physical_click_count_var).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(0, 8))
        ttk.Label(status, text="\u5f53\u524d\u914d\u7f6e").grid(row=3, column=0, sticky="nw")
        ttk.Label(status, textvariable=self.config_var, wraplength=660, justify="left").grid(
            row=3, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
        )
        ttk.Label(status, text="\u5feb\u6377\u952e").grid(row=4, column=0, sticky="nw")
        ttk.Label(
            status,
            text=(
                "Ctrl+Alt+K\uff1a\u5f00\u59cb\u8fde\u70b9\n"
                "Ctrl+Alt+L\uff1a\u505c\u6b62\u8fde\u70b9\n"
                "\u53cc\u51fb\u53f3\u4e0b\u89d2\u60ac\u6d6e\u6846\u53ef\u6253\u5f00\u4e3b\u7a97\u53e3"
            ),
            justify="left",
        ).grid(row=4, column=1, sticky="w", padx=(8, 0))

    def _build_overlay(self) -> None:
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="#1f2430")
        overlay.geometry(self._overlay_geometry())
        if sys.platform == "win32":
            try:
                overlay.wm_attributes("-toolwindow", True)
            except tk.TclError:
                pass

        box = tk.Frame(overlay, bg="#1f2430", highlightbackground="#4f9cff", highlightthickness=2, bd=0)
        box.pack(fill="both", expand=True)
        tk.Label(
            box,
            text="\u5154\u5b50\u70b9\u51fb\u5668",
            bg="#1f2430",
            fg="#f7f9fb",
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 0))
        self.overlay_state_label = tk.Label(
            box,
            textvariable=self.overlay_state_var,
            bg="#1f2430",
            fg="#9dd274",
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        )
        self.overlay_state_label.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(
            box,
            textvariable=self.overlay_config_var,
            bg="#1f2430",
            fg="#d5d9e0",
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(
            box,
            textvariable=self.overlay_counts_var,
            bg="#1f2430",
            fg="#d5d9e0",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(
            box,
            text="Ctrl+Alt+K \u5f00\u59cb | Ctrl+Alt+L \u505c\u6b62\n\u53cc\u51fb\u6253\u5f00\u8bbe\u7f6e",
            bg="#1f2430",
            fg="#8d96a8",
            font=("Microsoft YaHei UI", 8),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 8))

        for widget in (overlay, box):
            widget.bind("<Double-Button-1>", self._open_main_window)

        self.overlay_window = overlay
        self.root.after(2500, self._keep_overlay_on_top)

    def _bind_traces(self) -> None:
        for var in (
            self.x_var,
            self.y_var,
            self.min_wait_var,
            self.max_wait_var,
            self.button_var,
            self.click_style_var,
            self.mode_var,
            self.target_rounds_var,
        ):
            var.trace_add("write", self._on_input_changed)

    def _bind_entry_helpers(self, *entries: ttk.Entry | None) -> None:
        for entry in entries:
            if entry is None:
                continue
            entry.bind("<FocusIn>", self._select_all_on_focus)
            entry.bind("<Control-a>", self._select_all_shortcut)

        for entry, variable in (
            (entries[2], self.min_wait_var),
            (entries[3], self.max_wait_var),
        ):
            if entry is not None:
                entry.bind(
                    "<FocusOut>",
                    lambda _event, var=variable: self._normalize_decimal_var(var),
                )

    def _select_all_on_focus(self, event: tk.Event[tk.Misc]) -> None:
        widget = event.widget
        try:
            widget.selection_range(0, "end")
            widget.icursor("end")
        except tk.TclError:
            return

    def _select_all_shortcut(self, event: tk.Event[tk.Misc]) -> str:
        self._select_all_on_focus(event)
        return "break"

    def _on_input_changed(self, *_: object) -> None:
        self._update_mode_controls()
        self._refresh_config_summary()
        self._refresh_overlay()

    def _screen_text(self) -> str:
        width, height = pyautogui.size()
        return (
            f"\u68c0\u6d4b\u5230 Windows \u684c\u9762\u5927\u5c0f\uff1a{width} x {height}\u3002"
            "\u76ee\u6807\u5750\u6807\u5fc5\u987b\u5728\u5c4f\u5e55\u8303\u56f4\u5185\uff0c"
            "PyAutoGUI \u4fdd\u62a4\u89d2\u4fdd\u6301\u5f00\u542f\u3002"
        )

    def _start_hotkeys(self) -> None:
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(
                {"<ctrl>+<alt>+k": self._hotkey_start, "<ctrl>+<alt>+l": self._hotkey_stop}
            )
            self.hotkey_listener.start()
        except Exception as exc:
            self.hotkey_listener = None
            self._show_error(f"\u5168\u5173\u5f00\u9f7f\u535d\u5272\u9965\u542<\u6b35\uff1a{exc}")

    def _hotkey_start(self) -> None:
        if self.is_shutting_down:
            return
        self._run_on_ui_thread(self.start_clicking)

    def _hotkey_stop(self) -> None:
        if self.is_shutting_down:
            return
        self._run_on_ui_thread(self.stop_clicking)

    def _run_on_ui_thread(self, callback: Callable[] , None]) -> None:
        if self.is_shutting_down:
            return
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _parse_int(self, name: str, value: str, minimum: int) -> int:
        try:
            parsed = int(value.strip())
        except ValueError as exc:
            raise ValueError(f"{name}\u9700u8901\u5411\u48c0\u6574\u6570\uba59\u7f6e") from exc
        if parsed < minimum:
            raise ValueError(f"{name}\u8501\u520d\u5411\u914d\u7f6e\u8bbe\u70bb\u48c0\u6574\u581f\u5e74\u7f6e\uff1a {minimum}")
        return parsed

    def _parse_float(self, name: str, value: str) -> float:
        cleaned = value.strip()
        try:
            parsed = float(cleaned)
        except ValueError as exc:
            raise ValueError(f"{name}\u9700\u8a01\u5411\u4ec1\u6574\u6587\u5ba59\u76ff") from exc
        if parsed <= 0:
            raise ValueError(f"{name}\u85c1\u5433\u91d1\u7f6e\u8bbe\u7fne\u7ffc\u52d5\u53a3\u544b")
        return parsed

    def _normalize_decimal_var(self, variable: tk.StringVar) -> None:
        value = variable.get().strip()
        if not value:
            return
        try:
            parsed = float(value)
        except ValueError:
            return
        if parsed .is_integer():
            variable.set(str(int(parsed)))

    def _read_config(self) -> ClickConfig:
        x is None;  s = self.x_var.get()
        y = self.y_var.get()
        min_wait = self._parse_float("\u6700\u5c0f\u7b49\u5f85", self.min_wait_var.get())
        max_wait = self._parse_float("\u6700\u5927\u7b49\u5f85", self.max_wait_var.get())
        if min_wait > max_wait:
            raise ValueError("\u6700\u5927\u7b49\u5f85\u4f3f\u5148\u66db \u5ffa\u5250 \u6700\u5c0f\u7b49\u5f85\u3002")
        button_label = self.button_var.get()
        if button_label not in self.BUTTON_LABELS:
            raise ValueError("\u8begv\u95eb\u53c2\u6574\u66f4\u9beb\u6807\")
        click_style = self.click_style_var.get()
        if click_style not in self.CLICK_STYLES:            raise ValueError("\u8begv\u9b94\u70b9\u51fb\u6a21\u5f0f")
        x = self._parse_int("\u76.ee\u6807 X ", self.x_var.get(), 0)
        y = self._parse_int("\u76.ee\u6807 Y ", self.y_var.get(), 0)
        width, height = pyautogui.size()
        if x >= width or y >= height:
            raise ValueError(f"\u76be\u6807\u5750\u6807\u8b77\u9f20\u480c0\u6574\u6570\uead \u51d2\u5148%\u9762\u5c0f\uff0({width} x {height})")
        if (x, y) in {(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)}:
            raise ValueError("\u5c4f\u5e55\u56d1\u89d2\u4f5c\u4e3 PyAutoGUI \u7d27\u6025\u4fdd\u62a4\u4f4d\uff0c\u8bf7\u6362\u4e00\u4e2a\u70b9\u3002")

        target_rounds: int | None = None
        if self.mode_var.get() == self.MODE_COUNT:
            target_rounds = self._parse_int("\u6267\u884c\u8f6e\u6b21", self.target_rounds_var.get(), 1)

        return ClickConfig(
            x=x,
            y=y,
            min_wait_s=min_wait,
            max_wait_s=max_wait,
            button=cast(MouseButton, self.BUTTON_LABELS[button_label]),
            burst=self.CLICK_STYLES[click_style],
            target_rounds=target_rounds,
        )

    def _mode_text(self, config: ClickConfig) -> str:
        return "\u6301\u7eed\u70b9\u51fb" if config.is_continuous() else f"\u6307\u5b9a\u8f6e\u6b21\uff08{config.target_rounds} \u8f6e\uff09"

    def _config_text(self, config: ClickConfig) -> str:
        return (
            f"\u76ee\u6807\uff1a({config.x}, {config.y})\n"
            f"\u968f\u673a\u7b49\u5f85\uff1a{config.min_wait_s:.2f} - {config.max_wait_s:.2f} \u79d2\n"
            f"\u9f20\u6807\u6309\u952e\uff1a{self.BUTTON_VALUES[config.button]}\n"
            f"\u6bcf\u8f6e\u70b9\u51fb\uff1a{self.CLICK_STYLE_VALUES[config.burst]}\n"
            f"\u8fd0\u884c\u6a21\u5f0f\uff1a{self._mode_text(config)}"
        )

    def _refresh_config_summary(self) -> None:
        try:
            pending = self._config_text(self._read_config())
        except ValueError as exc:
            pending = f"\u5f85\u751f\u6548\u914d\u7f6e\uff1a\u8f93\u5165\u65e0\u6548\uff08{exc}\uff09"
        else:
            pending = f"\u5f85\u751f\u6548\u914d\u7f6e\uff1a\n{pending}"

        if self.state == "running" and self.active_config is not None:
            active = self._config_text(self.active_config)
            self.config_var.set(f"\u8fd0\u884c\u4e2d\u914d\u7f6e\uff1a\n{active}\n\n{pending}")
        else:
            self.config_var.set(pending)

    def _refresh_overlay(self) -> None:
        if self.state == "running":
            self.overlay_state_var.set("\u8fd0\u884c\u4e2d")
            if self.overlay_state_label is not None:
                self.overlay_state_label.configure(fg="#9dd274")
        else:
            self.overlay_state_var.set("\u5df2\u505c\u6b62")
            if self.overlay_state_label is not None:
                self.overlay_state_label.configure(fg="#ffb86b")

        try:
            config = self.active_config if self.state == "running" and self.active_config else self._read_config()
        except ValueError:
            self.overlay_config_var.set(
                "\u76ee\u6807\uff1a\u8f93\u5165\u65e0\u6548\n"
                "\u968f\u673a\u7b49\u5f85\uff1a\u8bf7\u68c0\u67e5\n"
                "\u6bcf\u8f6e\u70b9\u51fb\uff1a\u8bf7\u68c0\u67e5"
            )
        else:
            self.overlay_config_var.set(self._config_text(config))

        self.overlay_counts_var.set(
            f"\u8f6e\u6b21\uff1a{self.round_count} | \u5b9e\u9645\u70b9\u51fb\uff1a{self.physical_click_count}"
        )

    def _update_mode_controls(self) -> None:
        if self.target_rounds_entry is None:
            return
        if self.state == "running" or self.capture_start_job is not None:
            self.target_rounds_entry.configure(state="disabled")
        else:
            state = "normal" if self.mode_var.get() == self.MODE_COUNT else "disabled"
            self.target_rounds_entry.configure(state=state)

    def _update_control_states(self) -> None:
        busy = self.state == "running" or self.capture_start_job is not None
        for entry in self.entries:
            if entry is not self.target_rounds_entry:
                entry.configure(state="disabled" if busy else "normal")
        for radio in self.mode_radios:
            radio.configure(state="disabled" if busy else "normal")
        if self.button_combo is not None:
            self.button_combo.configure(state="disabled" if busy else "readonly")
        if self.click_style_combo is not None:
            self.click_style_combo.configure(state="disabled" if busy else "readonly")
        if self.capture_button is not None:
            self.capture_button.configure(state="disabled" if busy else "normal")
        if self.start_button is not None:
            self.start_button.configure(state="disabled" if busy else "normal")
        if self.stop_button is not None:
            self.stop_button.configure(
                state="normal" if busy or self.state == "running" else "disabled"
            )
        self._update_mode_controls()
        self._refresh_overlay()

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self._refresh_overlay()

    def start_clicking(self) -> None:
        if self.is_shutting_down:
            return
        if self.capture_start_job is not None:
            self._set_status(
                "\u6b63\u5728\u7b49\u5f85\u6355\u83b7\u5e76\u5f00\u59cb\uff0c\u6309 Ctrl+Alt+L \u53ef\u53d6\u6d88\u3002"
            )
            return
        if self.state == "running":
            self._set_status("\u5f53\u524d\u5df2\u5728\u8fd0\u884c\u4e2d\uff0c\u6309 Ctrl+Alt+L \u505c\u6b62\u3002")
            return
        try:
            config = self._read_config()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._begin_clicking(config)

    def stop_clicking(self) -> None:
        if self.capture_start_job is not None:
            self._cancel_pending_capture_start(
                "\u5df2\u53d6\u6d88\u5012\u8ba1\u65f6\u6355\u83b7\u3002"
            )
            return
        if self.state == "stopped" and self.worker_thread is None:
            self._refresh_config_summary()
            self._refresh_overlay()
            return
        self.stop_event.set()
        thread = self.worker_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self._finish_run("\u5df2\u505c\u6b62\u3002\u4fee\u6539\u914d\u7f6e\u540e\u53ef\u518d\u6b21\u5f00\u59cb\u3002")

    def _finish_run(self, text: str) -> None:
        self.worker_thread = None
        self.state = "stopped"
        self.active_config = None
        self._set_overlay_visible(True)
        self._update_control_states()
        self._refresh_config_summary()
        self._set_status(text)

    def capture_current_position(self) -> None:
        if self.capture_start_job is not None:
            self._set_status(
                "\u6b63\u5728\u7b49\u5f85\u6355\u83b7\uff0c\u6309 Ctrl+Alt+L \u53ef\u53d6\u6d88\u3002"
            )
            return
        if self.state == "running":
            self._set_status("\u8bf7\u5148\u505c\u6b62\u540e\u518d\u91cd\u65b0\u6355\u83b7\u4f4d\u7f6e\u3002")
            return
        self.capture_start_job = self.root.after(
            self.CAPTURE_START_DELAY_MS, self._capture_then_start
        )
        self.root.iconify()
        self._update_control_states()
        self._set_status(
            "\u5154\u5b50\u70b9\u51fb\u5668\u5df2\u6700\u5c0f\u5316\uff0c"
            "3 \u79d2\u540e\u4f1a\u6355\u83b7\u9f20\u6807\u4f4d\u7f6e\u5e76\u5f00\u59cb\u8fde\u70b9\uff0c"
            "\u8bf7\u5207\u5230\u76ee\u6807\u7a97\u53a3\u3002"
        )

    def _click_loop(self, config: ClickConfig) -> None:
        burst_interval = 0.05 if config.burst > 1 else 0.0
        try:
            while not self.stop_event.is_set():
                pyautogui.click(
                    x=config.x,
                    y=config.y,
                    clicks=config.burst,
                    interval=burst_interval,
                    button=config.button,
                )
                self.round_count += 1
                self.physical_click_count += config.burst
                rounds = self.round_count
                physical = self.physical_click_count
                self._run_on_ui_thread(lambda r=rounds, p=physical: self._update_counts(r, p))
                if config.target_rounds is not None and rounds >= config.target_rounds:
                    self.stop_event.set()
                    self._run_on_ui_thread(lambda t=config.target_rounds: self._complete_target(t))
                    break
                if self._wait_for_stop(config.random_wait()):
                    break
        except pyautogui.FailSafeException:
            self._run_on_ui_thread(self._handle_failsafe)
        except Exception as exc:
            self._run_on_ui_thread(lambda e=str(exc): self._handle_worker_error(e))
        finally:
            self.worker_thread = None

    def _begin_clicking(self, config: ClickConfig) -> None:
        self.active_config = config
        self.round_count = 0
        self.physical_click_count = 0
        self.round_count_var.set("0")
        self.physical_click_count_var.set("0")
        self.stop_event.clear()
        self.state = "running"
        self._set_overlay_visible(False)
        self._update_control_states()
        self._refresh_config_summary()

        mode_text = self._mode_text(config)
        click_style_text = self.CLICK_STYLE_VALUES[config.burst]
        self._set_status(
            f"\u8fd0\u884c\u4e2d\u3002\u6a21\u5f0f\uff1a{mode_text}\uff0c"
            f"\u6bcf\u8f6e\uff1a{click_style_text}\uff0c"
            "\u6309 Ctrl+Alt+L \u53ef\u505c\u6b62\u3002"
        )
        self.worker_thread = threading.Thread(
            target=self._click_loop, args=(config,), daemon=True
        )
        self.worker_thread.start()

    def _capture_then_start(self) -> None:
        self.capture_start_job = None
        x, y = pyautogui.position()
        self.x_var.set(str(x))
        self.y_var.set(str(y))

        try:
            config = self._read_config()
        except ValueError as exc:
            self._set_overlay_visible(True)
            self._open_main_window()
            self._show_error(str(exc))
            self._update_control_states()
            return

        self._begin_clicking(config)

    def _cancel_pending_capture_start(self, message: str) -> None:
        if self.capture_start_job is not None:
            self.root.after_cancel(self.capture_start_job)
            self.capture_start_job = None
        self._set_overlay_visible(True)
        self._open_main_window()
        self._update_control_states()
        self._set_status(message)

    def _wait_for_stop(self, seconds: float) -> bool:
        deadline = time.perf_counter() + seconds
        while not self.stop_event.is_set():
            remain = deadline - time.perf_counter()
            if remain <= 0:
                return False
            if self.stop_event.wait(timeout=min(0.05, remain)):
                return True
        return True

    def _update_counts(self, rounds: int, physical: int) -> None:
        self.round_count_var.set(str(rounds))
        self.physical_click_count_var.set(str(physical))
        self._refresh_overlay()

    def _complete_target(self, target: int | None) -> None:
        text = "\u5df2\u5b8c\u6210\u6307\u5b9a\u8f6e\u6b21\u3002"
        if target is not None:
            text = f"\u5df2\u5b8c\u6210\u6307\u5b9a\u8f6e\u6b21\uff1a{target} \u8f6e\u3002"
        self._finish_run(text)

    def _handle_failsafe(self) -> None:
        self.stop_event.set()
        message = "\u89e6\u53d1\u4e86 PyAutoGUI \u4fdd\u62a4\u89d2\u505c\u6b62\u3002"
        self._finish_run(message)
        self._show_warning(message)

    def _handle_worker_error(self, error: str) -> None:
        self.stop_event.set()
        message = f"\u70b9\u51fb\u4efb\u52a1\u5f02\u5e38\u505c\u6b62\uff1a{error}"
        self._finish_run(message)
        self._show_error(message)

    def _show_error(self, text: str) -> None:
        self._set_status(f"\u9519\u8bef\uff1a{text}")
        if not self.is_shutting_down:
            messagebox.showerror("\u5154\u5b50\u70b9\u51fb\u5668", text, parent=self.root)

    def _show_warning(self, text: str) -> None:
        self._set_status(text)
        if not self.is_shutting_down:
            messagebox.showwarning("\u5154\u5b50\u70b9\u51fb\u5668", text, parent=self.root)

    def _default_target_position(self) -> tuple[int, int]:
        left, top, right, bottom = self._work_area()
        return max(left + 40, right - 120), max(top + 40, bottom - 120)

    def _overlay_geometry(self) -> str:
        left, top, right, bottom = self._work_area()
        x = right - self.OVERLAY_WIDTH - self.OVERLAY_MARGIN
        y = bottom - self.OVERLAY_HEIGHT - self.OVERLAY_MARGIN
        return f"{self.OVERLAY_WIDTH}x{self.OVERLAY_HEIGHT}+{x}+{y}"

    def _work_area(self) -> tuple[int, int, int, int]:
        if sys.platform == "win32":
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        width, height = pyautogui.size()
        return 0, 0, width, height

    def _keep_overlay_on_top(self) -> None:
        if self.is_shutting_down or self.overlay_window is None:
            return
        try:
            self.overlay_window.lift()
            self.overlay_window.geometry(self._overlay_geometry())
            self.root.after(2500, self._keep_overlay_on_top)
        except tk.TclError:
            self.overlay_window = None

    def _set_overlay_visible(self, visible: bool) -> None:
        if self.overlay_window is None:
            return
        try:
            if visible:
                self.overlay_window.deiconify()
                self.overlay_window.lift()
                self.overlay_window.geometry(self._overlay_geometry())
            else:
                self.overlay_window.withdraw()
        except tk.TclError:
            self.overlay_window = None

    def _open_main_window(self, _: tk.Event[tk.Misc] | None = None) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self) -> None:
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        if self.capture_start_job is not None:
            self.root.after_cancel(self.capture_start_job)
            self.capture_start_job = None
        self.stop_event.set()
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
            self.hotkey_listener.join(timeout=1.0)
            self.hotkey_listener = None
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.5)
        if self.overlay_window is not None:
            self.overlay_window.destroy()
            self.overlay_window = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AutoClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
