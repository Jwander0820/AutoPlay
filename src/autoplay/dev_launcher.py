from __future__ import annotations

import sys
import threading
import webbrowser
from dataclasses import replace
from pathlib import Path
from tkinter import BooleanVar, END, StringVar, Tk, Text, filedialog, messagebox
from tkinter import ttk

from . import api
from .adb import AdbClient, parse_device_serials
from .emulator_profiles import PROFILES, first_existing_adb_candidate, get_profile, profile_id_to_label, profile_label_to_id
from .local_config import LOCAL_CONFIG_PATH, LocalConfig, load_local_config, save_local_config
from .paths import resolve_adb_path
from .recorder_server import RecorderServerReady, capture_recorder_screenshot, create_recorder_server


DEFAULT_TAP_X = "100"
DEFAULT_TAP_Y = "100"
DEFAULT_SCROLL_DISTANCE = "700"


class AutoPlayDevLauncher(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AutoPlay 開發測試工具")
        self.geometry("1060x760")
        self.server_ready: RecorderServerReady | None = None
        self.server_thread: threading.Thread | None = None
        self.local_config = load_local_config()

        self.profile_label = StringVar(value=profile_id_to_label(self.local_config.emulator_profile))
        self.adb_path = StringVar(value=self.local_config.adb_path or self._profile_adb_default())
        self.serial = StringVar(value=self.local_config.serial or "")
        self.connect_targets = StringVar(value=", ".join(self.local_config.connect_targets))
        self.script_path = StringVar(value=self.local_config.script_path)
        self.screenshot_path = StringVar(value=self.local_config.screenshot_path)
        self.recorder_port = StringVar(value=str(self.local_config.recorder_port))
        self.tap_x = StringVar(value=DEFAULT_TAP_X)
        self.tap_y = StringVar(value=DEFAULT_TAP_Y)
        self.scroll_distance = StringVar(value=DEFAULT_SCROLL_DISTANCE)
        self.allow_device_input = BooleanVar(value=self.local_config.allow_device_input)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log(f"Python: {sys.executable}")
        self._log(f"本機設定檔: {LOCAL_CONFIG_PATH}")
        self._log("若 Python 不是你的 venv，請在 PyCharm Project Interpreter 指到正確的 venv。")

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(root, text="環境與本機預設", padding=10)
        settings.pack(fill="x")
        ttk.Label(settings, text="模擬器 Profile").grid(row=0, column=0, sticky="w", pady=3)
        profile_combo = ttk.Combobox(
            settings,
            textvariable=self.profile_label,
            values=[profile.label for profile in PROFILES],
            state="readonly",
            width=32,
        )
        profile_combo.grid(row=0, column=1, sticky="w", pady=3)
        profile_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_profile_defaults())

        self._entry(settings, "ADB 路徑", self.adb_path, row=1, width=92)
        ttk.Button(settings, text="選擇 adb.exe", command=self.browse_adb).grid(row=1, column=2, padx=(6, 0))
        self._entry(settings, "裝置 serial", self.serial, row=2, width=40)
        self._entry(settings, "連線 targets", self.connect_targets, row=3, width=72)
        self._entry(settings, "腳本輸出", self.script_path, row=4, width=64)
        ttk.Button(settings, text="選擇腳本", command=self.browse_script).grid(row=4, column=2, padx=(6, 0))
        self._entry(settings, "截圖路徑", self.screenshot_path, row=5, width=64)
        ttk.Button(settings, text="選擇截圖", command=self.browse_screenshot).grid(row=5, column=2, padx=(6, 0))
        self._entry(settings, "Recorder port (0=自動)", self.recorder_port, row=6, width=16)
        ttk.Checkbutton(settings, text="允許 Recorder UI 發送真實點擊/手勢", variable=self.allow_device_input).grid(row=7, column=1, sticky="w", pady=(6, 0))

        config_buttons = ttk.Frame(settings)
        config_buttons.grid(row=8, column=1, sticky="w", pady=(8, 0))
        ttk.Button(config_buttons, text="套用 Profile 預設", command=self.apply_profile_defaults).pack(side="left", padx=(0, 6))
        ttk.Button(config_buttons, text="儲存本機預設", command=self.save_defaults).pack(side="left", padx=(0, 6))
        ttk.Button(config_buttons, text="重新載入本機預設", command=self.reload_defaults).pack(side="left")

        checks = ttk.LabelFrame(root, text="ADB 診斷", padding=10)
        checks.pack(fill="x", pady=(10, 0))
        self._button_row(
            checks,
            [
                ("偵測裝置", self.detect_devices),
                ("連線 targets", self.connect_targets_now),
                ("Doctor 檢查", self.run_doctor),
                ("擷取截圖", self.capture_screenshot),
                ("一鍵煙霧測試", self.run_smoke_test),
            ],
            row=0,
        )

        actions = ttk.LabelFrame(root, text="裝置操作", padding=10)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Label(actions, text="Tap X").grid(row=0, column=0, sticky="w")
        ttk.Entry(actions, textvariable=self.tap_x, width=8).grid(row=0, column=1, sticky="w", padx=(4, 12))
        ttk.Label(actions, text="Y").grid(row=0, column=2, sticky="w")
        ttk.Entry(actions, textvariable=self.tap_y, width=8).grid(row=0, column=3, sticky="w", padx=(4, 12))
        ttk.Button(actions, text="模擬點擊", command=self.dry_run_tap).grid(row=0, column=4, padx=4)
        ttk.Button(actions, text="真實點擊", command=self.real_tap).grid(row=0, column=5, padx=4)

        ttk.Label(actions, text="滑動距離").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(actions, textvariable=self.scroll_distance, width=8).grid(row=1, column=1, sticky="w", padx=(4, 12), pady=(8, 0))
        ttk.Button(actions, text="模擬下滑", command=self.dry_run_scroll).grid(row=1, column=4, padx=4, pady=(8, 0))
        ttk.Button(actions, text="真實下滑", command=self.real_scroll).grid(row=1, column=5, padx=4, pady=(8, 0))

        recorder = ttk.LabelFrame(root, text="Recorder UI", padding=10)
        recorder.pack(fill="x", pady=(10, 0))
        ttk.Button(recorder, text="啟動 Recorder UI", command=self.start_recorder_ui).grid(row=0, column=0, padx=4)
        ttk.Button(recorder, text="停止 Recorder UI", command=self.stop_recorder_ui).grid(row=0, column=1, padx=4)

        log_frame = ttk.LabelFrame(root, text="執行紀錄", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log = Text(log_frame, height=18, wrap="word")
        self.log.pack(fill="both", expand=True)

    def _entry(self, parent: ttk.Frame, label: str, variable: StringVar, row: int, width: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=variable, width=width).grid(row=row, column=1, sticky="we", pady=3)
        parent.columnconfigure(1, weight=1)

    def _button_row(self, parent: ttk.Frame, buttons: list[tuple[str, object]], row: int) -> None:
        for column, (text, command) in enumerate(buttons):
            ttk.Button(parent, text=text, command=command).grid(row=row, column=column, padx=4, pady=2, sticky="w")

    def _profile_id(self) -> str:
        return profile_label_to_id(self.profile_label.get())

    def _profile(self):
        return get_profile(self._profile_id())

    def _profile_adb_default(self) -> str:
        return first_existing_adb_candidate(get_profile(self.local_config.emulator_profile)) or resolve_adb_path()

    def _adb_path(self) -> str:
        return self.adb_path.get().strip()

    def _serial(self) -> str | None:
        value = self.serial.get().strip()
        return value or None

    def _target_list(self) -> tuple[str, ...]:
        parts = [part.strip() for part in self.connect_targets.get().replace(";", ",").split(",")]
        return tuple(part for part in parts if part)

    def _current_config(self) -> LocalConfig:
        return replace(
            self.local_config,
            emulator_profile=self._profile_id(),
            adb_path=self._adb_path() or None,
            serial=self._serial(),
            connect_targets=self._target_list(),
            script_path=self.script_path.get().strip() or self.local_config.script_path,
            screenshot_path=self.screenshot_path.get().strip() or self.local_config.screenshot_path,
            recorder_port=self._int_field(self.recorder_port, "Recorder port"),
            allow_device_input=self.allow_device_input.get(),
        )

    def apply_profile_defaults(self) -> None:
        profile = self._profile()
        candidate = first_existing_adb_candidate(profile)
        if candidate:
            self.adb_path.set(candidate)
        if profile.connect_targets:
            self.connect_targets.set(", ".join(profile.connect_targets))
        self._log(f"已套用 Profile: {profile.label}")

    def save_defaults(self) -> None:
        try:
            self.local_config = self._current_config()
            path = save_local_config(self.local_config)
        except Exception as exc:
            messagebox.showerror("儲存失敗", str(exc))
            return
        self._log(f"已儲存本機預設: {path}")
        self._log("這個檔案已被 .gitignore 排除，不會進 git。")

    def reload_defaults(self) -> None:
        self.local_config = load_local_config()
        self.profile_label.set(profile_id_to_label(self.local_config.emulator_profile))
        self.adb_path.set(self.local_config.adb_path or self._profile_adb_default())
        self.serial.set(self.local_config.serial or "")
        self.connect_targets.set(", ".join(self.local_config.connect_targets))
        self.script_path.set(self.local_config.script_path)
        self.screenshot_path.set(self.local_config.screenshot_path)
        self.recorder_port.set(str(self.local_config.recorder_port))
        self.allow_device_input.set(self.local_config.allow_device_input)
        self._log(f"已重新載入本機預設: {LOCAL_CONFIG_PATH}")

    def browse_adb(self) -> None:
        path = filedialog.askopenfilename(title="選擇 adb.exe", filetypes=[("ADB executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.adb_path.set(path)

    def browse_script(self) -> None:
        path = filedialog.asksaveasfilename(title="選擇腳本輸出", defaultextension=".yml", filetypes=[("YAML", "*.yml *.yaml"), ("All files", "*.*")])
        if path:
            self.script_path.set(path)

    def browse_screenshot(self) -> None:
        path = filedialog.asksaveasfilename(title="選擇截圖路徑", defaultextension=".png", filetypes=[("PNG", "*.png"), ("All files", "*.*")])
        if path:
            self.screenshot_path.set(path)

    def _device_serials(self) -> list[str]:
        result = AdbClient(self._adb_path()).devices()
        self._log(" ".join(result.command))
        output = result.stdout_text().strip()
        if output:
            self._log(output)
        elif result.stderr.strip():
            self._log(result.stderr.strip())
        elif not result.ok:
            self._log(f"ADB devices failed: exit={result.returncode}")
        return parse_device_serials(result.stdout_text())

    def _ensure_serial(self) -> str | None:
        current = self._serial()
        if current:
            return current
        serials = self._device_serials()
        if not serials:
            self._log("沒有偵測到可用裝置。請確認模擬器已開啟，或按「連線 targets」。")
            return None
        selected = serials[0]
        self.after(0, lambda: self.serial.set(selected))
        self._log(f"已自動選擇 serial: {selected}")
        if len(serials) > 1:
            self._log(f"偵測到多個裝置，暫時使用第一個；需要時請手動改 serial。全部: {', '.join(serials)}")
        return selected

    def _int_field(self, value: StringVar, label: str) -> int:
        try:
            parsed = int(value.get())
        except ValueError as exc:
            raise ValueError(f"{label} 必須是整數。") from exc
        if parsed < 0:
            raise ValueError(f"{label} 不能是負數。")
        return parsed

    def _run_background(self, label: str, task) -> None:
        self._log(f"> {label}")

        def worker() -> None:
            try:
                task()
            except Exception as exc:
                self._log(f"ERROR: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _log(self, text: str) -> None:
        def append() -> None:
            self.log.insert(END, text + "\n")
            self.log.see(END)

        if threading.current_thread() is threading.main_thread():
            append()
        else:
            self.after(0, append)

    def detect_devices(self) -> None:
        def task() -> None:
            serials = self._device_serials()
            if serials and not self._serial():
                self.after(0, lambda: self.serial.set(serials[0]))
                self._log(f"已選擇 serial: {serials[0]}")
            if not serials:
                self._log("未找到裝置。可以先按「連線 targets」，或確認模擬器 ADB 已開啟。")

        self._run_background("偵測裝置", task)

    def connect_targets_now(self) -> None:
        def task() -> None:
            targets = self._target_list()
            if not targets:
                self._log("目前沒有設定 connect targets。")
                return
            adb = AdbClient(self._adb_path())
            for target in targets:
                result = adb.run(["connect", target])
                self._log(" ".join(result.command))
                self._log(result.stdout_text().strip() or result.stderr.strip() or f"exit={result.returncode}")
            serials = self._device_serials()
            if serials:
                self.after(0, lambda: self.serial.set(serials[0]))
                self._log(f"已選擇 serial: {serials[0]}")

        self._run_background("連線 targets", task)

    def run_doctor(self) -> None:
        def task() -> None:
            report = api.doctor(adb_path=self._adb_path(), serial=self._serial())
            for line in report.lines:
                self._log(line)

        self._run_background("Doctor 檢查", task)

    def capture_screenshot(self) -> None:
        def task() -> None:
            serial = self._ensure_serial()
            if serial is None:
                return
            result = api.screenshot(self.screenshot_path.get(), adb_path=self._adb_path(), serial=serial)
            self._log(" ".join(result.command))
            if result.ok:
                self._log(f"已寫入截圖: {Path(self.screenshot_path.get()).resolve()}")
            else:
                self._log(result.stderr.strip() or f"截圖失敗: exit={result.returncode}")

        self._run_background("擷取截圖", task)

    def run_smoke_test(self) -> None:
        def task() -> None:
            self._log("煙霧測試開始：devices -> doctor -> screenshot -> dry-run tap -> dry-run scroll")
            serials = self._device_serials()
            if not serials:
                self._log("煙霧測試停止：沒有裝置。")
                return
            serial = self._serial() or serials[0]
            self.after(0, lambda: self.serial.set(serial))
            report = api.doctor(adb_path=self._adb_path(), serial=serial)
            for line in report.lines:
                self._log(line)
            if not report.ok:
                self._log("煙霧測試停止：doctor 未通過。")
                return
            screenshot = api.screenshot(self.screenshot_path.get(), adb_path=self._adb_path(), serial=serial)
            self._log(" ".join(screenshot.command))
            if not screenshot.ok:
                self._log(screenshot.stderr.strip() or f"截圖失敗: exit={screenshot.returncode}")
                return
            tap = api.tap(self._int_field(self.tap_x, "Tap X"), self._int_field(self.tap_y, "Tap Y"), adb_path=self._adb_path(), serial=serial, execute=False)
            self._log(" ".join(tap.command))
            scroll = api.scroll("down", distance=self._int_field(self.scroll_distance, "滑動距離"), adb_path=self._adb_path(), serial=serial, execute=False)
            self._log(" ".join(scroll.command))
            self._log("煙霧測試完成：目前只做 dry-run，沒有真實點擊。")

        self._run_background("一鍵煙霧測試", task)

    def dry_run_tap(self) -> None:
        self._tap(execute=False)

    def real_tap(self) -> None:
        if messagebox.askyesno("確認真實點擊", "要送出真實點擊到模擬器嗎？"):
            self._tap(execute=True)

    def _tap(self, execute: bool) -> None:
        def task() -> None:
            serial = self._ensure_serial()
            if serial is None:
                return
            x = self._int_field(self.tap_x, "Tap X")
            y = self._int_field(self.tap_y, "Tap Y")
            result = api.tap(x, y, adb_path=self._adb_path(), serial=serial, execute=execute)
            self._log(" ".join(result.command))
            self._log("OK" if result.ok else result.stderr.strip() or f"exit={result.returncode}")

        self._run_background("真實點擊" if execute else "模擬點擊", task)

    def dry_run_scroll(self) -> None:
        self._scroll(execute=False)

    def real_scroll(self) -> None:
        if messagebox.askyesno("確認真實下滑", "要送出真實下滑到模擬器嗎？"):
            self._scroll(execute=True)

    def _scroll(self, execute: bool) -> None:
        def task() -> None:
            serial = self._ensure_serial()
            if serial is None:
                return
            distance = self._int_field(self.scroll_distance, "滑動距離")
            result = api.scroll("down", distance=distance, adb_path=self._adb_path(), serial=serial, execute=execute)
            self._log(" ".join(result.command))
            self._log("OK" if result.ok else result.stderr.strip() or f"exit={result.returncode}")

        self._run_background("真實下滑" if execute else "模擬下滑", task)

    def start_recorder_ui(self) -> None:
        if self.server_ready is not None:
            self._log(f"Recorder UI 已在執行: {self.server_ready.url}")
            webbrowser.open(self.server_ready.url)
            return

        def task() -> None:
            serial = self._ensure_serial()
            if serial is None:
                return
            self._log("啟動 Recorder UI 前會先擷取最新模擬器畫面。")
            capture = capture_recorder_screenshot(
                self.script_path.get(),
                self.screenshot_path.get(),
                port=self._int_field(self.recorder_port, "Recorder port"),
                capture=True,
                adb_path=self._adb_path(),
                serial=serial,
                allow_device_input=self.allow_device_input.get(),
            )
            result = capture.screenshot_result
            if result is not None and not result.ok:
                self._log(result.stderr.strip() or f"啟動 Recorder UI 前截圖失敗: exit={result.returncode}")
                return
            self._log(f"已擷取最新畫面: {Path(self.screenshot_path.get()).resolve()}")
            ready = create_recorder_server(capture.config)
            self.server_ready = ready
            self.server_thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            self.server_thread.start()
            self._log(f"Recorder UI: {ready.url}")
            self._log(f"腳本: {capture.config.script_path}")
            self._log(f"截圖: {capture.config.screenshot_path}")
            webbrowser.open(ready.url)

        self._run_background("啟動 Recorder UI", task)

    def stop_recorder_ui(self) -> None:
        if self.server_ready is None:
            self._log("Recorder UI 目前沒有執行。")
            return
        self.server_ready.server.shutdown()
        self.server_ready.server.server_close()
        self._log("Recorder UI 已停止。")
        self.server_ready = None
        self.server_thread = None

    def _on_close(self) -> None:
        if self.server_ready is not None:
            self.stop_recorder_ui()
        self.destroy()


def main() -> None:
    app = AutoPlayDevLauncher()
    app.mainloop()
