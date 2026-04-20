from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adb import AdbClient
from .doctor import run_doctor
from .image_match import ImageError, match_template_file
from .paths import resolve_adb_path
from .runner import RunnerError, run_script_file
from .script import Region, ScriptError
from .validation import format_report, validate_script_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoplay", description="BlueStacks ADB POC controller.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check BlueStacks ADB readiness.")
    doctor.add_argument("--adb-path", help="Override HD-Adb.exe path for this check.")
    doctor.add_argument("--serial", help="ADB serial to target.")
    doctor.set_defaults(func=_doctor)

    screenshot = subparsers.add_parser("screenshot", help="Capture a PNG screenshot through ADB.")
    screenshot.add_argument("--out", required=True, help="Output PNG path.")
    screenshot.add_argument("--adb-path", help="Override HD-Adb.exe path.")
    screenshot.add_argument("--serial", help="ADB serial to target.")
    screenshot.set_defaults(func=_screenshot)

    tap = subparsers.add_parser("tap", help="Tap a coordinate through ADB; dry-run unless --yes is passed.")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)
    tap.add_argument("--yes", action="store_true", help="Actually send the tap.")
    tap.add_argument("--adb-path", help="Override HD-Adb.exe path.")
    tap.add_argument("--serial", help="ADB serial to target.")
    tap.set_defaults(func=_tap)

    run = subparsers.add_parser("run", help="Run an AutoPlay YAML script.")
    run.add_argument("script", help="Path to YAML script.")
    run.add_argument("--execute-taps", action="store_true", help="Actually send tap steps; otherwise taps are dry-run.")
    run.add_argument("--report-out", help="Write a JSON run report, including partial progress on runner failures.")
    run.set_defaults(func=_run)

    validate = subparsers.add_parser("validate", help="Validate an AutoPlay YAML script without touching ADB.")
    validate.add_argument("script", help="Path to YAML script.")
    validate.set_defaults(func=_validate)

    match = subparsers.add_parser("match", help="Match a PNG template against a PNG screenshot without touching ADB.")
    match.add_argument("source", help="Source screenshot PNG path.")
    match.add_argument("template", help="Template PNG path.")
    match.add_argument("--threshold", type=float, default=0.95, help="Required match score from 0 to 1.")
    match.add_argument("--tolerance", type=int, default=0, help="Per-channel pixel tolerance from 0 to 255.")
    match.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"), help="Limit search area.")
    match.set_defaults(func=_match)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RunnerError, ScriptError, ImageError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _doctor(args: argparse.Namespace) -> int:
    report = run_doctor(profile_adb_path=args.adb_path, serial=args.serial)
    for line in report.lines:
        print(line)
    return 0 if report.ok else 1


def _screenshot(args: argparse.Namespace) -> int:
    adb = AdbClient(adb_path=resolve_adb_path(args.adb_path), serial=args.serial)
    out_path = Path(args.out)
    result = adb.screencap(out_path)
    if not result.ok:
        print(f"ERROR: screencap failed with exit {result.returncode}: {result.stderr}", file=sys.stderr)
        return 1
    print(f"Wrote screenshot: {out_path}")
    return 0


def _tap(args: argparse.Namespace) -> int:
    adb = AdbClient(adb_path=resolve_adb_path(args.adb_path), serial=args.serial)
    result = adb.tap(args.x, args.y, dry_run=not args.yes)
    print(" ".join(result.command))
    if result.dry_run:
        print("Dry-run only. Pass --yes to send the tap.")
        return 0
    if not result.ok:
        print(f"ERROR: tap failed with exit {result.returncode}: {result.stderr}", file=sys.stderr)
        return 1
    print("Tap sent.")
    return 0


def _run(args: argparse.Namespace) -> int:
    try:
        report = run_script_file(args.script, dry_run_taps=not args.execute_taps)
    except RunnerError as exc:
        if args.report_out and exc.report is not None:
            _write_report(args.report_out, exc.report.to_dict())
        raise
    for line in report.executed:
        print(line)
    if not args.execute_taps:
        print("Tap steps were dry-run. Pass --execute-taps to send them.")
    if args.report_out:
        _write_report(args.report_out, report.to_dict())
    return 0


def _validate(args: argparse.Namespace) -> int:
    report = validate_script_file(args.script)
    for line in format_report(report):
        print(line)
    return 0 if report.ok else 1


def _match(args: argparse.Namespace) -> int:
    if args.threshold < 0 or args.threshold > 1:
        raise ScriptError("--threshold must be between 0 and 1.")
    if args.tolerance < 0 or args.tolerance > 255:
        raise ScriptError("--tolerance must be between 0 and 255.")
    region = _parse_match_region(args.region)
    result = match_template_file(args.source, args.template, args.threshold, tolerance=args.tolerance, region=region)
    location = "none" if result.x is None or result.y is None else f"{result.x},{result.y}"
    print(f"score={result.score:.3f} matched={str(result.matched).lower()} location={location}")
    return 0 if result.matched else 1


def _parse_match_region(raw_region: list[int] | None) -> Region | None:
    if raw_region is None:
        return None
    x, y, width, height = raw_region
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ScriptError("--region must use non-negative x/y and positive width/height.")
    return Region(x=x, y=y, width=width, height=height)


def _write_report(path: str, report: dict) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
