from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass

from .adb import AdbClient, parse_device_serials
from .paths import DEFAULT_WINDOWS_ADB, ENV_ADB_PATH, KNOWN_WINDOWS_ADB_PATHS, is_wsl, path_exists_for_host, resolve_adb_path


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    lines: list[str]


def run_doctor(profile_adb_path: str | None = None, serial: str | None = None) -> DoctorReport:
    lines: list[str] = []
    ok = True
    adb_path = resolve_adb_path(profile_adb_path)

    lines.append(f"OS: {platform.system()} {platform.release()}")
    lines.append(f"Python: {sys.version.split()[0]}")
    if is_wsl():
        lines.append("Note: WSL detected. Windows Python is the first-class controller host for BlueStacks.")

    source = "profile"
    if os.environ.get(ENV_ADB_PATH):
        source = ENV_ADB_PATH
    elif not profile_adb_path:
        source = "default"
    lines.append(f"ADB path ({source}): {adb_path}")

    if not path_exists_for_host(adb_path):
        ok = False
        lines.append("FAIL: ADB executable was not found.")
        lines.append(f"Default BlueStacks path: {DEFAULT_WINDOWS_ADB}")
        lines.append("Known Windows ADB paths:")
        for candidate in KNOWN_WINDOWS_ADB_PATHS:
            lines.append(f"  - {candidate}")
        lines.append(f"Set {ENV_ADB_PATH} to the full adb.exe/HD-Adb.exe path if your emulator is installed elsewhere.")
        return DoctorReport(ok=ok, lines=lines)

    adb = AdbClient(adb_path=adb_path, serial=serial)
    devices_result = adb.devices()
    lines.append(f"ADB devices command: {' '.join(devices_result.command)}")
    if not devices_result.ok:
        ok = False
        lines.append(f"FAIL: adb devices exited with {devices_result.returncode}.")
        if devices_result.stderr:
            lines.append(devices_result.stderr.strip())
        lines.extend(_adb_help_lines())
        return DoctorReport(ok=ok, lines=lines)

    serials = parse_device_serials(devices_result.stdout_text())
    if not serials:
        ok = False
        lines.append("FAIL: No connected Android emulator/device was reported by ADB.")
        lines.extend(_adb_help_lines())
        return DoctorReport(ok=ok, lines=lines)

    lines.append(f"Connected devices: {', '.join(serials)}")
    lines.append("OK: Android emulator ADB looks reachable.")
    return DoctorReport(ok=ok, lines=lines)


def _adb_help_lines() -> list[str]:
    return [
        "Open your emulator settings and enable Android Debug Bridge / ADB debugging.",
        "For LDPlayer, use its bundled adb.exe if the default BlueStacks HD-Adb.exe cannot see the emulator.",
        r"Then test in Windows PowerShell: cd 'C:\Program Files\BlueStacks_nxt'; .\HD-Adb.exe devices",
        r"LDPlayer example: cd 'C:\LDPlayer\LDPlayer9'; .\adb.exe devices",
    ]
