from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class AdbResult:
    command: list[str]
    returncode: int
    stdout: bytes = b""
    stderr: str = ""
    timed_out: bool = False
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def stdout_text(self) -> str:
        return self.stdout.decode("utf-8", errors="replace")


class AdbClient:
    def __init__(self, adb_path: str, serial: str | None = None, timeout: float = 15.0):
        self.adb_path = adb_path
        self.serial = serial
        self.timeout = timeout

    def build_command(self, args: Sequence[str]) -> list[str]:
        command = [self.adb_path]
        if self.serial:
            command.extend(["-s", self.serial])
        command.extend(str(arg) for arg in args)
        return command

    def run(self, args: Sequence[str], timeout: float | None = None) -> AdbResult:
        command = self.build_command(args)
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout if timeout is None else timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            return AdbResult(command=command, returncode=127, stderr=str(exc))
        except PermissionError as exc:
            return AdbResult(command=command, returncode=126, stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
            return AdbResult(command=command, returncode=124, stdout=stdout, stderr=stderr, timed_out=True)

        return AdbResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr.decode("utf-8", errors="replace"),
        )

    def devices(self) -> AdbResult:
        return self.run(["devices", "-l"])

    def device_serials(self) -> list[str]:
        result = self.devices()
        if not result.ok:
            return []
        return parse_device_serials(result.stdout_text())

    def screencap(self, out_path: Path) -> AdbResult:
        result = self.run(["exec-out", "screencap", "-p"], timeout=30.0)
        if result.ok and result.stdout:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(result.stdout)
        return result

    def tap(self, x: int, y: int, dry_run: bool = False) -> AdbResult:
        args = ["shell", "input", "tap", str(x), str(y)]
        command = self.build_command(args)
        if dry_run:
            return AdbResult(command=command, returncode=0, stderr="dry-run: command not executed", dry_run=True)
        return self.run(args)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int, dry_run: bool = False) -> AdbResult:
        args = ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
        command = self.build_command(args)
        if dry_run:
            return AdbResult(command=command, returncode=0, stderr="dry-run: command not executed", dry_run=True)
        return self.run(args)

    def back(self, dry_run: bool = False) -> AdbResult:
        args = ["shell", "input", "keyevent", "BACK"]
        command = self.build_command(args)
        if dry_run:
            return AdbResult(command=command, returncode=0, stderr="dry-run: command not executed", dry_run=True)
        return self.run(args)


def parse_device_serials(devices_output: str) -> list[str]:
    serials: list[str] = []
    for raw_line in devices_output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials
