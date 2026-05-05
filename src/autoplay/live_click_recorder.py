from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .image_match import read_png
from .recorder import append_step_to_script
from .script import ScriptError


class LiveClickRecorderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClientGeometry:
    left: int
    top: int
    width: int
    height: int
    target_width: int
    target_height: int


@dataclass(frozen=True)
class LiveClick:
    screen_x: int
    screen_y: int
    x: int
    y: int
    label: str


def map_click_to_target(screen_x: int, screen_y: int, geometry: ClientGeometry) -> tuple[int, int] | None:
    if geometry.width <= 0 or geometry.height <= 0 or geometry.target_width <= 0 or geometry.target_height <= 0:
        raise LiveClickRecorderError("Window and target dimensions must be positive.")
    local_x = screen_x - geometry.left
    local_y = screen_y - geometry.top
    if local_x < 0 or local_y < 0 or local_x >= geometry.width or local_y >= geometry.height:
        return None
    return (
        round(local_x * geometry.target_width / geometry.width),
        round(local_y * geometry.target_height / geometry.height),
    )


def append_live_click(script_path: str | Path, x: int, y: int, label: str) -> None:
    if x < 0 or y < 0:
        raise ScriptError("live click coordinates must be non-negative.")
    append_step_to_script(script_path, {"type": "tap", "x": x, "y": y, "label": label})


def run_windows_live_click_recorder(
    script_path: str | Path,
    screenshot_path: str | Path | None = None,
    window_title: str = "BlueStacks",
    label_prefix: str = "live click",
    max_clicks: int | None = None,
) -> list[LiveClick]:
    if sys.platform != "win32":
        raise LiveClickRecorderError("Live click recording is only available from Windows Python.")
    if max_clicks is not None and max_clicks <= 0:
        raise LiveClickRecorderError("max_clicks must be positive when provided.")

    target_size = _target_size_from_screenshot(screenshot_path)
    return _WindowsMouseHook(script_path=Path(script_path), window_title=window_title, label_prefix=label_prefix, target_size=target_size, max_clicks=max_clicks).run()


def _target_size_from_screenshot(screenshot_path: str | Path | None) -> tuple[int, int] | None:
    if screenshot_path is None:
        return None
    image = read_png(screenshot_path)
    return image.width, image.height


class _WindowsMouseHook:
    def __init__(
        self,
        script_path: Path,
        window_title: str,
        label_prefix: str,
        target_size: tuple[int, int] | None,
        max_clicks: int | None,
    ):
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.script_path = script_path
        self.window_title = window_title.lower()
        self.label_prefix = label_prefix
        self.target_size = target_size
        self.max_clicks = max_clicks
        self.clicks: list[LiveClick] = []
        self.hook = None
        self.callback_ref = None

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt", POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        self.POINT = POINT
        self.MSLLHOOKSTRUCT = MSLLHOOKSTRUCT

    def run(self) -> list[LiveClick]:
        ctypes = self.ctypes
        user32 = self.user32
        WH_MOUSE_LL = 14
        WM_LBUTTONDOWN = 0x0201
        PM_REMOVE = 0x0001

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, self.wintypes.WPARAM, self.wintypes.LPARAM)

        def callback(n_code, w_param, l_param):
            if n_code >= 0 and w_param == WM_LBUTTONDOWN:
                data = ctypes.cast(l_param, ctypes.POINTER(self.MSLLHOOKSTRUCT)).contents
                self._handle_click(data.pt.x, data.pt.y)
            return user32.CallNextHookEx(self.hook, n_code, w_param, l_param)

        self.callback_ref = HOOKPROC(callback)
        self.hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self.callback_ref, self.kernel32.GetModuleHandleW(None), 0)
        if not self.hook:
            raise LiveClickRecorderError("Could not install Windows mouse hook.")

        msg = self.wintypes.MSG()
        try:
            while True:
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                if self.max_clicks is not None and len(self.clicks) >= self.max_clicks:
                    break
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            user32.UnhookWindowsHookEx(self.hook)
        return self.clicks

    def _handle_click(self, screen_x: int, screen_y: int) -> None:
        hwnd = self._window_from_point(screen_x, screen_y)
        if not hwnd:
            return
        title = self._window_title(hwnd)
        if self.window_title and self.window_title not in title.lower():
            return
        geometry = self._client_geometry(hwnd)
        mapped = map_click_to_target(screen_x, screen_y, geometry)
        if mapped is None:
            return
        x, y = mapped
        label = f"{self.label_prefix} {len(self.clicks) + 1}"
        append_live_click(self.script_path, x, y, label)
        self.clicks.append(LiveClick(screen_x=screen_x, screen_y=screen_y, x=x, y=y, label=label))
        print(f"recorded {label}: {x},{y}")

    def _window_from_point(self, screen_x: int, screen_y: int):
        GA_ROOT = 2
        point = self.POINT(screen_x, screen_y)
        hwnd = self.user32.WindowFromPoint(point)
        if not hwnd:
            return None
        return self.user32.GetAncestor(hwnd, GA_ROOT) or hwnd

    def _window_title(self, hwnd) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buffer = self.ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def _client_geometry(self, hwnd) -> ClientGeometry:
        rect = self.wintypes.RECT()
        if not self.user32.GetClientRect(hwnd, self.ctypes.byref(rect)):
            raise LiveClickRecorderError("Could not read emulator client rectangle.")
        origin = self.POINT(0, 0)
        if not self.user32.ClientToScreen(hwnd, self.ctypes.byref(origin)):
            raise LiveClickRecorderError("Could not map emulator client origin.")
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        target_width, target_height = self.target_size or (width, height)
        return ClientGeometry(left=origin.x, top=origin.y, width=width, height=height, target_width=target_width, target_height=target_height)
