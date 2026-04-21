from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .adb import AdbClient, AdbResult
from .doctor import DoctorReport, run_doctor
from .image_match import MatchResult, match_template_file
from .paths import resolve_adb_path
from .runner import RunnerError, RunnerReport, run_script_file
from .script import Region, ScriptError
from .validation import ValidationReport, validate_script_file


def doctor(adb_path: str | None = None, serial: str | None = None) -> DoctorReport:
    return run_doctor(profile_adb_path=adb_path, serial=serial)


def screenshot(out: str | Path, adb_path: str | None = None, serial: str | None = None) -> AdbResult:
    adb = _adb_client(adb_path=adb_path, serial=serial)
    return adb.screencap(Path(out))


def tap(x: int, y: int, adb_path: str | None = None, serial: str | None = None, execute: bool = False) -> AdbResult:
    if not isinstance(x, int) or not isinstance(y, int) or x < 0 or y < 0:
        raise ScriptError("tap coordinates must be non-negative integers.")
    adb = _adb_client(adb_path=adb_path, serial=serial)
    return adb.tap(x, y, dry_run=not execute)


def validate(script_path: str | Path) -> ValidationReport:
    return validate_script_file(script_path)


def run(
    script_path: str | Path,
    execute_taps: bool = False,
    report_out: str | Path | None = None,
    adb_path: str | None = None,
    serial: str | None = None,
) -> RunnerReport:
    validation = validate(script_path)
    if not validation.ok:
        messages = "\n".join(issue.message for issue in validation.errors)
        raise RunnerError(f"Script validation failed:\n{messages}")

    try:
        report = run_script_file(script_path, dry_run_taps=not execute_taps, adb_path=adb_path, serial=serial)
    except RunnerError as exc:
        if report_out is not None and exc.report is not None:
            _write_report(report_out, exc.report.to_dict())
        raise

    if report_out is not None:
        _write_report(report_out, report.to_dict())
    return report


def match(
    source: str | Path,
    template: str | Path,
    threshold: float = 0.95,
    tolerance: int = 0,
    region: Region | Sequence[int] | None = None,
) -> MatchResult:
    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
        raise ScriptError("threshold must be between 0 and 1.")
    if not isinstance(tolerance, int) or tolerance < 0 or tolerance > 255:
        raise ScriptError("tolerance must be between 0 and 255.")
    return match_template_file(
        source,
        template,
        float(threshold),
        tolerance=tolerance,
        region=_coerce_region(region),
    )


def _adb_client(adb_path: str | None = None, serial: str | None = None) -> AdbClient:
    return AdbClient(adb_path=resolve_adb_path(adb_path), serial=serial)


def _coerce_region(region: Region | Sequence[int] | None) -> Region | None:
    if region is None or isinstance(region, Region):
        return region
    try:
        x, y, width, height = region
    except (TypeError, ValueError) as exc:
        raise ScriptError("region must contain exactly four integers: x, y, width, height.") from exc
    if not all(isinstance(part, int) for part in (x, y, width, height)):
        raise ScriptError("region must contain exactly four integers: x, y, width, height.")
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ScriptError("region must use non-negative x/y and positive width/height.")
    return Region(x=x, y=y, width=width, height=height)


def _write_report(path: str | Path, report: dict) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
