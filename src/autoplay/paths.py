from __future__ import annotations

import os
import platform
from pathlib import Path

DEFAULT_WINDOWS_ADB = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
KNOWN_WINDOWS_ADB_PATHS = (
    DEFAULT_WINDOWS_ADB,
    r"C:\LDPlayer\LDPlayer9\adb.exe",
    r"C:\Program Files\LDPlayer\LDPlayer9\adb.exe",
    r"C:\leidian\LDPlayer9\adb.exe",
    r"D:\LDPlayer\LDPlayer9\adb.exe",
)
ENV_ADB_PATH = "AUTOPLAY_ADB"


def is_wsl() -> bool:
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def windows_path_to_wsl(path: str) -> str:
    if len(path) < 3 or path[1:3] != ":\\":
        return path
    drive = path[0].lower()
    rest = path[3:].replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


def resolve_adb_path(profile_path: str | None = None) -> str:
    override = os.environ.get(ENV_ADB_PATH)
    chosen = override or profile_path or default_adb_path()
    if os.name != "nt" and is_wsl() and len(chosen) >= 3 and chosen[1:3] == ":\\":
        return windows_path_to_wsl(chosen)
    return chosen


def default_adb_path() -> str:
    for candidate in KNOWN_WINDOWS_ADB_PATHS:
        if path_exists_for_host(candidate):
            return candidate
    return DEFAULT_WINDOWS_ADB


def path_exists_for_host(path: str) -> bool:
    return Path(path).exists()
