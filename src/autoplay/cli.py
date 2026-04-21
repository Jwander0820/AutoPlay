from __future__ import annotations

import argparse
import sys

from . import api
from .agent_runner import agent_run_script
from .agent_tools import SafetyError
from .click_map import capture_click_map, write_click_map
from .image_match import ImageError
from .live_click_recorder import LiveClickRecorderError, run_windows_live_click_recorder
from .recorder_server import capture_recorder_screenshot, create_recorder_server
from .recorder import record_script
from .runner import RunnerError
from .script import ScriptError
from .validation import format_report


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

    click_map = subparsers.add_parser("click-map", help="Create a local HTML script builder from a screenshot.")
    click_map.add_argument("screenshot", help="Screenshot PNG path to use or create.")
    click_map.add_argument("--out", required=True, help="Output HTML path.")
    click_map.add_argument("--script-out", help="Default script filename used by the HTML download button.")
    click_map.add_argument("--capture", action="store_true", help="Capture the screenshot first through ADB.")
    click_map.add_argument("--adb-path", help="Override HD-Adb.exe path when --capture is used.")
    click_map.add_argument("--serial", help="ADB serial to target when --capture is used.")
    click_map.set_defaults(func=_click_map)

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

    record = subparsers.add_parser("record", help="Interactively append steps to an AutoPlay YAML script.")
    record.add_argument("script", help="Path to YAML script to create or update.")
    record.set_defaults(func=_record)

    record_ui = subparsers.add_parser("record-ui", help="Start a local browser recorder that saves YAML directly.")
    record_ui.add_argument("script", help="Path to YAML script to create or update.")
    record_ui.add_argument("--screenshot", required=True, help="Screenshot PNG path to use or create.")
    record_ui.add_argument("--capture", action="store_true", help="Capture the screenshot first through ADB.")
    record_ui.add_argument("--host", default="127.0.0.1", help="Host for the local recorder server.")
    record_ui.add_argument("--port", type=int, default=8765, help="Port for the local recorder server.")
    record_ui.add_argument("--adb-path", help="Override HD-Adb.exe path when --capture is used.")
    record_ui.add_argument("--serial", help="ADB serial to target when --capture is used.")
    record_ui.add_argument("--allow-device-input", action="store_true", help="Allow the browser recorder to send taps before refreshing screenshots.")
    record_ui.set_defaults(func=_record_ui)

    record_clicks = subparsers.add_parser("record-clicks", help="Experimentally record live Windows clicks inside a BlueStacks window.")
    record_clicks.add_argument("script", help="Path to YAML script to append tap steps to.")
    record_clicks.add_argument("--screenshot", help="Screenshot PNG used to scale window clicks into ADB coordinates.")
    record_clicks.add_argument("--window-title", default="BlueStacks", help="Only record clicks from a window whose title contains this text.")
    record_clicks.add_argument("--label-prefix", default="live click", help="Label prefix for appended tap steps.")
    record_clicks.add_argument("--max-clicks", type=int, help="Stop after this many clicks. Otherwise press Ctrl+C.")
    record_clicks.set_defaults(func=_record_clicks)

    agent_run = subparsers.add_parser("agent-run", help="Run a script through the AI-facing safety session.")
    agent_run.add_argument("script", help="Path to YAML script.")
    agent_run.add_argument("--artifact-root", default="artifacts", help="Root for reports, screenshots, templates, and audit logs.")
    agent_run.add_argument("--report-out", help="Write the runner JSON report here. Defaults under artifact root.")
    agent_run.add_argument("--audit-out", help="Write the agent audit JSONL here. Defaults under artifact root.")
    agent_run.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls.")
    agent_run.add_argument("--intent", default="daily task dry run", help="Short safe intent label for audit logs.")
    agent_run.add_argument("--execute-taps", action="store_true", help="Request real tap execution.")
    agent_run.add_argument("--allow-device-input", action="store_true", help="Allow real device input when --execute-taps is also set.")
    agent_run.add_argument("--adb-path", help="Override HD-Adb.exe path for script execution.")
    agent_run.add_argument("--serial", help="ADB serial to target during script execution.")
    agent_run.set_defaults(func=_agent_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RunnerError, SafetyError, LiveClickRecorderError, ScriptError, ImageError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _doctor(args: argparse.Namespace) -> int:
    report = api.doctor(adb_path=args.adb_path, serial=args.serial)
    for line in report.lines:
        print(line)
    return 0 if report.ok else 1


def _screenshot(args: argparse.Namespace) -> int:
    result = api.screenshot(args.out, adb_path=args.adb_path, serial=args.serial)
    if not result.ok:
        _print_adb_failure("screencap", result, adb_path=args.adb_path, serial=args.serial)
        return 1
    print(f"Wrote screenshot: {args.out}")
    return 0


def _click_map(args: argparse.Namespace) -> int:
    if args.capture:
        report = capture_click_map(args.screenshot, args.out, script_path=args.script_out, adb_path=args.adb_path, serial=args.serial)
        result = report.screenshot_result
        if result is not None and not result.ok:
            _print_adb_failure("screencap", result, adb_path=args.adb_path, serial=args.serial)
            return 1
    else:
        report = write_click_map(args.screenshot, args.out, script_path=args.script_out)
    print(f"Screenshot: {report.screenshot_path}")
    print(f"Click map: {report.html_path}")
    if report.script_path is not None:
        print(f"Script download name: {report.script_path.name}")
    return 0


def _tap(args: argparse.Namespace) -> int:
    result = api.tap(args.x, args.y, adb_path=args.adb_path, serial=args.serial, execute=args.yes)
    print(" ".join(result.command))
    if result.dry_run:
        print("Dry-run only. Pass --yes to send the tap.")
        return 0
    if not result.ok:
        _print_adb_failure("tap", result, adb_path=args.adb_path, serial=args.serial)
        return 1
    print("Tap sent.")
    return 0


def _run(args: argparse.Namespace) -> int:
    report = api.run(args.script, execute_taps=args.execute_taps, report_out=args.report_out)
    for line in report.executed:
        print(line)
    if not args.execute_taps:
        print("Tap steps were dry-run. Pass --execute-taps to send them.")
    return 0


def _validate(args: argparse.Namespace) -> int:
    report = api.validate(args.script)
    for line in format_report(report):
        print(line)
    return 0 if report.ok else 1


def _match(args: argparse.Namespace) -> int:
    result = api.match(
        args.source,
        args.template,
        threshold=args.threshold,
        tolerance=args.tolerance,
        region=args.region,
    )
    location = "none" if result.x is None or result.y is None else f"{result.x},{result.y}"
    print(f"score={result.score:.3f} matched={str(result.matched).lower()} location={location}")
    return 0 if result.matched else 1


def _record(args: argparse.Namespace) -> int:
    record_script(args.script, input_stream=sys.stdin, output_stream=sys.stdout)
    return 0


def _record_ui(args: argparse.Namespace) -> int:
    capture = capture_recorder_screenshot(
        args.script,
        args.screenshot,
        host=args.host,
        port=args.port,
        capture=args.capture,
        adb_path=args.adb_path,
        serial=args.serial,
        allow_device_input=args.allow_device_input,
    )
    result = capture.screenshot_result
    if result is not None and not result.ok:
        _print_adb_failure("screencap", result, adb_path=args.adb_path, serial=args.serial)
        return 1

    ready = create_recorder_server(capture.config)
    print(f"Recorder UI: {ready.url}")
    print(f"Script: {capture.config.script_path}")
    print(f"Screenshot: {capture.config.screenshot_path}")
    if capture.config.allow_device_input:
        print("Device input is enabled for Tap + Capture.")
    else:
        print("Device input is disabled; use Capture Latest after manual actions.")
    print("Press Ctrl+C to stop.")
    try:
        ready.server.serve_forever()
    except KeyboardInterrupt:
        print("\nRecorder stopped.")
    finally:
        ready.server.server_close()
    return 0


def _print_adb_failure(context: str, result, adb_path: str | None = None, serial: str | None = None) -> None:
    stderr = result.stderr.strip()
    print(f"ERROR: {context} failed with exit {result.returncode}: {stderr}", file=sys.stderr)
    if serial or "more than one device/emulator" not in stderr:
        return

    report = api.doctor(adb_path=adb_path)
    serial_line = next((line for line in report.lines if line.startswith("Connected devices: ")), "")
    serials = [item.strip() for item in serial_line.removeprefix("Connected devices: ").split(",") if item.strip()]
    if serials:
        print("ADB found multiple devices. Choose one serial and rerun with --serial:", file=sys.stderr)
        for candidate in serials:
            print(f"  --serial {candidate}", file=sys.stderr)
        print(f"Example: add --serial {serials[0]} to your command.", file=sys.stderr)
    else:
        print("ADB found multiple devices. Run `py -m autoplay doctor` and rerun with the correct --serial value.", file=sys.stderr)


def _record_clicks(args: argparse.Namespace) -> int:
    print("Experimental live click recorder. It only writes YAML and never sends taps.")
    print("Click inside the target BlueStacks window. Press Ctrl+C to stop.")
    clicks = run_windows_live_click_recorder(
        args.script,
        screenshot_path=args.screenshot,
        window_title=args.window_title,
        label_prefix=args.label_prefix,
        max_clicks=args.max_clicks,
    )
    print(f"Recorded {len(clicks)} click(s) into {args.script}.")
    return 0


def _agent_run(args: argparse.Namespace) -> int:
    summary = agent_run_script(
        args.script,
        artifact_root=args.artifact_root,
        report_out=args.report_out,
        audit_out=args.audit_out,
        step_budget=args.step_budget,
        execute_taps=args.execute_taps,
        allow_device_input=args.allow_device_input,
        intent=args.intent,
        adb_path=args.adb_path,
        serial=args.serial,
    )
    for line in format_report(summary.validation):
        print(line)
    for line in summary.report.executed:
        print(line)
    if not summary.report.dry_run_taps:
        print("Agent run sent real tap steps.")
    else:
        print("Agent run kept tap steps dry-run.")
    print(f"Report: {summary.report_path}")
    print(f"Audit: {summary.audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
