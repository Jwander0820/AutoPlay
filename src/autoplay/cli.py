from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

from . import api
from .agent_runner import agent_run_script
from .agent_tools import SafetyError
from .ai_adapter import get_ai_adapter_payload
from .ai_bridge import AiBridge
from .ai_chat import AiChatConfig, AiChatError, run_ai_chat
from .ai_client import AiClientError, run_ai_client_smoke
from .ai_examples import get_ai_examples_payload
from .ai_mcp import McpStdioConfig, run_mcp_stdio
from .ai_mcp_client import AiMcpSmokeError, run_ai_mcp_smoke
from .ai_server import AiToolServerConfig, create_ai_tool_server
from .ai_schemas import get_ai_schema_payload
from .calibration import (
    CalibrationProfile,
    adjust_scroll_distance,
    calibration_notes_path_for_serial,
    calibration_path_for_serial,
    draft_calibration_profile,
    load_calibration_for_serial,
    render_calibration_note,
    save_calibration_note,
    save_calibration_profile,
)
from .click_map import capture_click_map, write_click_map
from .image_match import ImageError, read_png
from .live_click_recorder import LiveClickRecorderError, run_windows_live_click_recorder
from .recorder_server import capture_recorder_screenshot, create_recorder_server
from .recorder import record_script
from .runner import RunnerError
from .script import ScriptError
from .validation import format_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoplay", description="ADB controller for Android emulator automation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check Android emulator ADB readiness.")
    doctor.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path for this check.")
    doctor.add_argument("--serial", help="ADB serial to target.")
    doctor.set_defaults(func=_doctor)

    screenshot = subparsers.add_parser("screenshot", help="Capture a PNG screenshot through ADB.")
    screenshot.add_argument("--out", required=True, help="Output PNG path.")
    screenshot.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    screenshot.add_argument("--serial", help="ADB serial to target.")
    screenshot.set_defaults(func=_screenshot)

    click_map = subparsers.add_parser("click-map", help="Create a local HTML script builder from a screenshot.")
    click_map.add_argument("screenshot", help="Screenshot PNG path to use or create.")
    click_map.add_argument("--out", required=True, help="Output HTML path.")
    click_map.add_argument("--script-out", help="Default script filename used by the HTML download button.")
    click_map.add_argument("--capture", action="store_true", help="Capture the screenshot first through ADB.")
    click_map.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path when --capture is used.")
    click_map.add_argument("--serial", help="ADB serial to target when --capture is used.")
    click_map.set_defaults(func=_click_map)

    tap = subparsers.add_parser("tap", help="Tap a coordinate through ADB; dry-run unless --yes is passed.")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)
    tap.add_argument("--yes", action="store_true", help="Actually send the tap.")
    tap.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    tap.add_argument("--serial", help="ADB serial to target.")
    tap.set_defaults(func=_tap)

    swipe = subparsers.add_parser("swipe", help="Swipe through ADB; dry-run unless --yes is passed.")
    swipe.add_argument("x1", type=int)
    swipe.add_argument("y1", type=int)
    swipe.add_argument("x2", type=int)
    swipe.add_argument("y2", type=int)
    swipe.add_argument("--duration-ms", type=int, default=300, help="Swipe duration in milliseconds.")
    swipe.add_argument("--yes", action="store_true", help="Actually send the swipe.")
    swipe.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    swipe.add_argument("--serial", help="ADB serial to target.")
    swipe.set_defaults(func=_swipe)

    drag = subparsers.add_parser("drag", help="Drag through ADB; dry-run unless --yes is passed.")
    drag.add_argument("x1", type=int)
    drag.add_argument("y1", type=int)
    drag.add_argument("x2", type=int)
    drag.add_argument("y2", type=int)
    drag.add_argument("--duration-ms", type=int, default=700, help="Drag duration in milliseconds.")
    drag.add_argument("--yes", action="store_true", help="Actually send the drag.")
    drag.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    drag.add_argument("--serial", help="ADB serial to target.")
    drag.set_defaults(func=_drag)

    scroll = subparsers.add_parser("scroll", help="Scroll through ADB; dry-run unless --yes is passed.")
    scroll.add_argument("direction", choices=["up", "down", "left", "right"])
    scroll.add_argument("--distance", type=int, help="Scroll distance in pixels. Defaults to 700.")
    scroll.add_argument("--duration-ms", type=int, default=400, help="Scroll duration in milliseconds.")
    scroll.add_argument("--yes", action="store_true", help="Actually send the scroll.")
    scroll.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    scroll.add_argument("--serial", help="ADB serial to target.")
    scroll.add_argument("--calibrated", action="store_true", help="Use the serial calibration profile for distance and screen size.")
    scroll.add_argument("--artifact-root", default="artifacts", help="Root containing calibration profiles when --calibrated is used.")
    scroll.set_defaults(func=_scroll)

    back = subparsers.add_parser("back", help="Send Android back through ADB; dry-run unless --yes is passed.")
    back.add_argument("--yes", action="store_true", help="Actually send the back keyevent.")
    back.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path.")
    back.add_argument("--serial", help="ADB serial to target.")
    back.set_defaults(func=_back)

    calibration = subparsers.add_parser("calibration", help="Create or inspect local gesture calibration profiles.")
    calibration_subparsers = calibration.add_subparsers(dest="calibration_command", required=True)
    calibration_show = calibration_subparsers.add_parser("show", help="Show the calibration profile that record-ui would use.")
    calibration_show.add_argument("--serial", help="ADB serial used to select the calibration profile.")
    calibration_show.add_argument("--artifact-root", default="artifacts", help="Root containing calibration profiles.")
    calibration_show.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    calibration_show.set_defaults(func=_calibration_show)

    calibration_write = calibration_subparsers.add_parser("write", help="Write a gesture calibration profile JSON file.")
    calibration_write.add_argument("--serial", help="ADB serial for this calibration profile.")
    calibration_write.add_argument("--artifact-root", default="artifacts", help="Root for the default calibration profile path.")
    calibration_write.add_argument("--out", help="Explicit output JSON path. Defaults under artifact root.")
    calibration_write.add_argument("--screen-width", type=int, default=1080)
    calibration_write.add_argument("--screen-height", type=int, default=1920)
    calibration_write.add_argument("--from-screenshot", help="Use this PNG screenshot to fill screen width and height.")
    calibration_write.add_argument("--scroll-vertical-distance", type=int, default=700)
    calibration_write.add_argument("--scroll-horizontal-distance", type=int, default=700)
    calibration_write.add_argument("--default-swipe-duration-ms", type=int, default=400)
    calibration_write.add_argument("--default-drag-duration-ms", type=int, default=700)
    calibration_write.set_defaults(func=_calibration_write)

    calibration_guide = calibration_subparsers.add_parser("guide", help="Interactively derive and save a gesture calibration profile.")
    calibration_guide.add_argument("--serial", help="ADB serial for this calibration profile.")
    calibration_guide.add_argument("--artifact-root", default="artifacts", help="Root for calibration profiles and notes.")
    calibration_guide.add_argument("--from-screenshot", help="Use this PNG screenshot to fill screen width and height.")
    calibration_guide.add_argument("--duration-ms", type=int, default=400, help="Scroll duration used for previews and optional real tests.")
    calibration_guide.add_argument("--adjustment", type=int, default=80, help="Pixels to add/subtract when feedback is short or long.")
    calibration_guide.add_argument("--max-rounds", type=int, default=6, help="Maximum feedback rounds per scroll axis.")
    calibration_guide.add_argument("--yes", action="store_true", help="Allow optional one-scroll real tests after an additional prompt.")
    calibration_guide.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path when --yes real tests are confirmed.")
    calibration_guide.set_defaults(func=_calibration_guide)

    run = subparsers.add_parser("run", help="Run an AutoPlay YAML script.")
    run.add_argument("script", help="Path to YAML script.")
    run.add_argument("--execute-taps", action="store_true", help="Actually send tap and gesture steps; otherwise device input is dry-run.")
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
    record_ui.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path when --capture is used.")
    record_ui.add_argument("--serial", help="ADB serial to target when --capture is used.")
    record_ui.add_argument("--allow-device-input", action="store_true", help="Allow the browser recorder to send taps before refreshing screenshots.")
    record_ui.set_defaults(func=_record_ui)

    record_clicks = subparsers.add_parser("record-clicks", help="Experimentally record live Windows clicks inside a matching emulator window.")
    record_clicks.add_argument("script", help="Path to YAML script to append tap steps to.")
    record_clicks.add_argument("--screenshot", help="Screenshot PNG used to scale window clicks into ADB coordinates.")
    record_clicks.add_argument("--window-title", default="BlueStacks", help="Only record clicks from a window whose title contains this text. Use LDPlayer when recording LDPlayer.")
    record_clicks.add_argument("--label-prefix", default="live click", help="Label prefix for appended tap steps.")
    record_clicks.add_argument("--max-clicks", type=int, help="Stop after this many clicks. Otherwise press Ctrl+C.")
    record_clicks.set_defaults(func=_record_clicks)

    ai_tool = subparsers.add_parser("ai-tool", help="Run one local AI JSON tool request through the safety bridge.")
    ai_tool.add_argument("request", help="JSON request file, or '-' to read from stdin.")
    ai_tool.add_argument("--out", help="Optional response JSON output path. Defaults to stdout.")
    ai_tool.add_argument("--artifact-root", default="artifacts", help="Root for screenshots, reports, templates, and audit logs.")
    ai_tool.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_tool.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this bridge session.")
    ai_tool.add_argument("--allow-device-input", action="store_true", help="Allow real input only when the request also sets args.execute=true.")
    ai_tool.add_argument("--device-input-code", help="Require this code inside args.device_input_code before real device input is sent.")
    ai_tool.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path. Defaults to ignored local config when present.")
    ai_tool.add_argument("--serial", help="ADB serial to target. Defaults to ignored local config when present.")
    ai_tool.set_defaults(func=_ai_tool)

    ai_server = subparsers.add_parser("ai-server", help="Start a local HTTP server for AI JSON tool calls.")
    ai_server.add_argument("--host", default="127.0.0.1", help="Host for the local AI tool server.")
    ai_server.add_argument("--port", type=int, default=8787, help="Port for the local AI tool server. Use 0 to choose a free port.")
    ai_server.add_argument("--artifact-root", default="artifacts", help="Root for screenshots, reports, templates, and audit logs.")
    ai_server.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_server.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this server session.")
    ai_server.add_argument("--allow-device-input", action="store_true", help="Allow real input only when a request also sets args.execute=true.")
    ai_server.add_argument("--device-input-code", help="Require this code inside args.device_input_code before real device input is sent. Generated when omitted with --allow-device-input.")
    ai_server.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path. Defaults to ignored local config when present.")
    ai_server.add_argument("--serial", help="ADB serial to target. Defaults to ignored local config when present.")
    ai_server.set_defaults(func=_ai_server)

    ai_schemas = subparsers.add_parser("ai-schemas", help="Print machine-readable local AI tool schemas.")
    ai_schemas.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_schemas.set_defaults(func=_ai_schemas)

    ai_examples = subparsers.add_parser("ai-examples", help="Print machine-readable local AI tool example requests.")
    ai_examples.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_examples.set_defaults(func=_ai_examples)

    ai_chat = subparsers.add_parser("ai-chat", help="Ask a local/OpenAI chat model to use AutoPlay tools through the safety bridge.")
    ai_chat.add_argument("--provider", choices=["ollama", "lmstudio", "lm-studio", "openai"], required=True, help="Chat provider API to call.")
    ai_chat.add_argument("--model", required=True, help="Model name for the selected provider.")
    ai_chat.add_argument("--prompt", required=True, help="User request for the AI assistant.")
    ai_chat.add_argument("--base-url", help="Override provider base URL. Defaults: Ollama 11434, LM Studio 1234/v1, OpenAI /v1.")
    ai_chat.add_argument("--api-key", help="API key for OpenAI or compatible servers. OpenAI also reads OPENAI_API_KEY.")
    ai_chat.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    ai_chat.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    ai_chat.add_argument("--max-tool-calls", type=int, default=4, help="Maximum tool calls the model may request.")
    ai_chat.add_argument("--tool", action="append", help="Restrict the model to a specific AutoPlay tool. Repeat to allow more tools.")
    ai_chat.add_argument("--artifact-root", default="artifacts", help="Root for screenshots, reports, templates, and audit logs.")
    ai_chat.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_chat.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this chat session.")
    ai_chat.add_argument("--allow-device-input", action="store_true", help="Allow real input only when model tool args also set execute=true.")
    ai_chat.add_argument("--device-input-code", help="Require this code inside tool arguments before real device input is sent.")
    ai_chat.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path. Defaults to ignored local config when present.")
    ai_chat.add_argument("--serial", help="ADB serial to target. Defaults to ignored local config when present.")
    ai_chat.add_argument("--transcript-out", help="Optional sanitized transcript JSON output path.")
    ai_chat.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_chat.set_defaults(func=_ai_chat)

    ai_chat_smoke = subparsers.add_parser("ai-chat-smoke", help="Smoke-test provider chat tool-loop behavior without an external model.")
    ai_chat_smoke.add_argument("--artifact-root", default="artifacts", help="Root for generated smoke scripts, audit logs, and reports.")
    ai_chat_smoke.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_chat_smoke.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this smoke session.")
    ai_chat_smoke.add_argument("--transcript-out", help="Optional sanitized transcript JSON output path.")
    ai_chat_smoke.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_chat_smoke.set_defaults(func=_ai_chat_smoke)

    ai_adapter = subparsers.add_parser("ai-adapter", help="Print MCP/local-client adapter tool metadata.")
    ai_adapter.add_argument("--prefix-names", action="store_true", help="Prefix tool names with autoplay. for clients that share a tool namespace.")
    ai_adapter.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_adapter.set_defaults(func=_ai_adapter)

    ai_mcp_stdio = subparsers.add_parser("ai-mcp-stdio", help="Run a minimal MCP stdio server over the AI bridge.")
    ai_mcp_stdio.add_argument("--artifact-root", default="artifacts", help="Root for screenshots, reports, templates, and audit logs.")
    ai_mcp_stdio.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_mcp_stdio.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this MCP session.")
    ai_mcp_stdio.add_argument("--allow-device-input", action="store_true", help="Allow real input only when requests also set execute=true.")
    ai_mcp_stdio.add_argument("--device-input-code", help="Require this code inside tool arguments before real device input is sent.")
    ai_mcp_stdio.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path. Defaults to ignored local config when present.")
    ai_mcp_stdio.add_argument("--serial", help="ADB serial to target. Defaults to ignored local config when present.")
    ai_mcp_stdio.set_defaults(func=_ai_mcp_stdio)

    ai_mcp_smoke = subparsers.add_parser("ai-mcp-smoke", help="Smoke-test the local MCP stdio server in memory.")
    ai_mcp_smoke.add_argument("--example", help="Optional safe example request name to run through MCP tools/call, such as dry_run_tap.")
    ai_mcp_smoke.add_argument("--allow-real-examples", action="store_true", help="Allow examples that request real device input.")
    ai_mcp_smoke.add_argument("--artifact-root", default="artifacts", help="Root for screenshots, reports, templates, and audit logs.")
    ai_mcp_smoke.add_argument("--audit-out", help="Write the AI bridge audit JSONL here. Defaults under artifact root.")
    ai_mcp_smoke.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls for this smoke session.")
    ai_mcp_smoke.add_argument("--allow-device-input", action="store_true", help="Allow real input only when requests also set execute=true.")
    ai_mcp_smoke.add_argument("--device-input-code", help="Require this code inside tool arguments before real device input is sent.")
    ai_mcp_smoke.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path. Defaults to ignored local config when present.")
    ai_mcp_smoke.add_argument("--serial", help="ADB serial to target. Defaults to ignored local config when present.")
    ai_mcp_smoke.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_mcp_smoke.set_defaults(func=_ai_mcp_smoke)

    ai_smoke = subparsers.add_parser("ai-smoke", help="Smoke-test a running local AI tool server.")
    ai_smoke.add_argument("--base-url", default="http://127.0.0.1:8787", help="Base URL for a running ai-server.")
    ai_smoke.add_argument("--example", help="Optional example request name to POST to /tool, such as dry_run_tap.")
    ai_smoke.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds.")
    ai_smoke.add_argument("--allow-real-examples", action="store_true", help="Allow examples that request real device input.")
    ai_smoke.add_argument("--out", help="Optional output JSON path. Defaults to stdout.")
    ai_smoke.set_defaults(func=_ai_smoke)

    agent_run = subparsers.add_parser("agent-run", help="Run a script through the AI-facing safety session.")
    agent_run.add_argument("script", help="Path to YAML script.")
    agent_run.add_argument("--artifact-root", default="artifacts", help="Root for reports, screenshots, templates, and audit logs.")
    agent_run.add_argument("--report-out", help="Write the runner JSON report here. Defaults under artifact root.")
    agent_run.add_argument("--audit-out", help="Write the agent audit JSONL here. Defaults under artifact root.")
    agent_run.add_argument("--step-budget", type=int, default=20, help="Maximum number of agent tool calls.")
    agent_run.add_argument("--intent", default="daily task dry run", help="Short safe intent label for audit logs.")
    agent_run.add_argument("--execute-taps", action="store_true", help="Request real tap and gesture execution.")
    agent_run.add_argument("--allow-device-input", action="store_true", help="Allow real device input when --execute-taps is also set.")
    agent_run.add_argument("--adb-path", help="Override adb.exe/HD-Adb.exe path for script execution.")
    agent_run.add_argument("--serial", help="ADB serial to target during script execution.")
    agent_run.set_defaults(func=_agent_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RunnerError, SafetyError, LiveClickRecorderError, ScriptError, ImageError, AiChatError, AiClientError, AiMcpSmokeError, OSError) as exc:
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


def _swipe(args: argparse.Namespace) -> int:
    result = api.swipe(args.x1, args.y1, args.x2, args.y2, duration_ms=args.duration_ms, adb_path=args.adb_path, serial=args.serial, execute=args.yes)
    return _print_device_input_result("swipe", "Swipe sent.", "Dry-run only. Pass --yes to send the swipe.", result, args)


def _drag(args: argparse.Namespace) -> int:
    result = api.drag(args.x1, args.y1, args.x2, args.y2, duration_ms=args.duration_ms, adb_path=args.adb_path, serial=args.serial, execute=args.yes)
    return _print_device_input_result("drag", "Drag sent.", "Dry-run only. Pass --yes to send the drag.", result, args)


def _scroll(args: argparse.Namespace) -> int:
    distance = args.distance
    screen_width = 1080
    screen_height = 1920
    if args.calibrated:
        calibration = load_calibration_for_serial(args.serial, artifact_root=args.artifact_root)
        profile = calibration.profile
        if distance is None:
            distance = profile.distance_for_direction(args.direction)
        screen_width = profile.screen_width
        screen_height = profile.screen_height
        for warning in calibration.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    result = api.scroll(
        args.direction,
        distance=distance,
        duration_ms=args.duration_ms,
        adb_path=args.adb_path,
        serial=args.serial,
        execute=args.yes,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    return _print_device_input_result("scroll", "Scroll sent.", "Dry-run only. Pass --yes to send the scroll.", result, args)


def _back(args: argparse.Namespace) -> int:
    result = api.back(adb_path=args.adb_path, serial=args.serial, execute=args.yes)
    return _print_device_input_result("back", "Back sent.", "Dry-run only. Pass --yes to send the back keyevent.", result, args)


def _calibration_show(args: argparse.Namespace) -> int:
    result = load_calibration_for_serial(args.serial, artifact_root=args.artifact_root)
    if args.json:
        print(json.dumps(result.to_ui_dict(), indent=2, sort_keys=True))
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 1 if result.warnings else 0
    print(f"Calibration path: {result.path}")
    print(f"Loaded: {str(result.loaded).lower()}")
    profile = result.profile
    print(f"serial: {profile.serial or ''}")
    print(f"screen: {profile.screen_width}x{profile.screen_height}")
    print(f"scroll_vertical_distance: {profile.scroll_vertical_distance}")
    print(f"scroll_horizontal_distance: {profile.scroll_horizontal_distance}")
    print(f"default_swipe_duration_ms: {profile.default_swipe_duration_ms}")
    print(f"default_drag_duration_ms: {profile.default_drag_duration_ms}")
    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 1 if result.warnings else 0


def _calibration_write(args: argparse.Namespace) -> int:
    screen_width = args.screen_width
    screen_height = args.screen_height
    if args.from_screenshot:
        screenshot = read_png(args.from_screenshot)
        screen_width = screenshot.width
        screen_height = screenshot.height
    profile = CalibrationProfile(
        serial=args.serial,
        screen_width=screen_width,
        screen_height=screen_height,
        scroll_vertical_distance=args.scroll_vertical_distance,
        scroll_horizontal_distance=args.scroll_horizontal_distance,
        default_swipe_duration_ms=args.default_swipe_duration_ms,
        default_drag_duration_ms=args.default_drag_duration_ms,
    )
    out = args.out or calibration_path_for_serial(args.artifact_root, args.serial)
    path = save_calibration_profile(profile, out)
    print(f"Wrote calibration: {path}")
    print(f"screen: {profile.screen_width}x{profile.screen_height}")
    print(f"scroll_vertical_distance: {profile.scroll_vertical_distance}")
    print(f"scroll_horizontal_distance: {profile.scroll_horizontal_distance}")
    return 0


def _calibration_guide(args: argparse.Namespace) -> int:
    load_result = load_calibration_for_serial(args.serial, artifact_root=args.artifact_root)
    for warning in load_result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if load_result.warnings:
        return 1

    screen_width = load_result.profile.screen_width
    screen_height = load_result.profile.screen_height
    if args.from_screenshot:
        screenshot = read_png(args.from_screenshot)
        screen_width = screenshot.width
        screen_height = screenshot.height

    profile = draft_calibration_profile(load_result.profile, serial=args.serial, screen_width=screen_width, screen_height=screen_height)
    print("Guided gesture calibration")
    print(f"Profile path: {load_result.path}")
    print(f"Loaded existing profile: {str(load_result.loaded).lower()}")
    print(f"Screen: {profile.screen_width}x{profile.screen_height}")
    print(f"Real device input: {'enabled with confirmation' if args.yes else 'disabled'}")

    vertical = _calibrate_scroll_axis(args, profile, axis="vertical", direction="down", distance=profile.scroll_vertical_distance)
    profile = draft_calibration_profile(profile, scroll_vertical_distance=vertical)
    horizontal = _calibrate_scroll_axis(args, profile, axis="horizontal", direction="right", distance=profile.scroll_horizontal_distance)
    profile = draft_calibration_profile(profile, scroll_horizontal_distance=horizontal)

    print("Final calibration draft:")
    print(f"screen: {profile.screen_width}x{profile.screen_height}")
    print(f"scroll_vertical_distance: {profile.scroll_vertical_distance}")
    print(f"scroll_horizontal_distance: {profile.scroll_horizontal_distance}")

    if not _confirm("Save this calibration profile? Type yes to save: "):
        print("Calibration profile was not saved.")
        return 0

    profile_path = save_calibration_profile(profile, load_result.path or calibration_path_for_serial(args.artifact_root, args.serial))
    comments = _prompt("Optional tester comments for notes: ").strip()
    note = render_calibration_note(
        profile,
        screenshot_path=args.from_screenshot,
        tested_directions=("down", "right"),
        comments=comments,
    )
    note_path = save_calibration_note(note, calibration_notes_path_for_serial(args.artifact_root, args.serial))
    print(f"Wrote calibration: {profile_path}")
    print(f"Wrote notes: {note_path}")
    return 0


def _calibrate_scroll_axis(args: argparse.Namespace, profile: CalibrationProfile, axis: str, direction: str, distance: int) -> int:
    if args.max_rounds <= 0:
        raise ScriptError("calibration guide --max-rounds must be a positive integer.")
    current = distance
    for _round in range(args.max_rounds):
        print(f"{axis} scroll distance: {current}")
        preview = api.scroll(
            direction,
            distance=current,
            duration_ms=args.duration_ms,
            adb_path=args.adb_path,
            serial=args.serial,
            execute=False,
            screen_width=profile.screen_width,
            screen_height=profile.screen_height,
        )
        print("Preview command:")
        print(" ".join(preview.command))
        if args.yes and _confirm(f"Send one real {direction} scroll now? Type yes to run: "):
            # --yes opens the door to real input, but each individual scroll
            # still requires a fresh confirmation so calibration remains bounded.
            real = api.scroll(
                direction,
                distance=current,
                duration_ms=args.duration_ms,
                adb_path=args.adb_path,
                serial=args.serial,
                execute=True,
                screen_width=profile.screen_width,
                screen_height=profile.screen_height,
            )
            print(" ".join(real.command))
            if not real.ok:
                _print_adb_failure("calibration scroll", real, adb_path=args.adb_path, serial=args.serial)
                raise ScriptError("calibration real scroll failed.")
            print("Scroll sent.")
        feedback = _prompt(f"Feedback for {axis} distance [ok/short/long/<pixels>]: ")
        try:
            next_distance = adjust_scroll_distance(current, feedback, adjustment=args.adjustment)
        except ScriptError as exc:
            print(f"Invalid feedback: {exc}")
            continue
        if next_distance == current:
            return current
        current = next_distance
    print(f"Reached max rounds for {axis}; keeping distance {current}.")
    return current


def _confirm(prompt: str) -> bool:
    return _prompt(prompt).strip().lower() == "yes"


def _prompt(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError as exc:
        raise ScriptError("calibration guide requires interactive input.") from exc


def _run(args: argparse.Namespace) -> int:
    report = api.run(args.script, execute_taps=args.execute_taps, report_out=args.report_out)
    for line in report.executed:
        print(line)
    if not args.execute_taps:
        print("Tap and gesture steps were dry-run. Pass --execute-taps to send them.")
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
    calibration = load_calibration_for_serial(capture.config.serial, artifact_root=_default_artifact_root(capture.config.script_path))
    if calibration.loaded:
        print(f"Calibration: {calibration.path}")
    else:
        print(f"Calibration: defaults ({calibration.path})")
    if capture.config.allow_device_input:
        print("Device input is enabled for tap/gesture capture.")
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


def _default_artifact_root(script_path) -> str:
    script_parent = getattr(script_path, "parent", None)
    if script_parent is not None and script_parent.name == "scripts":
        return str(script_parent.parent / "artifacts")
    return "artifacts"


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


def _print_device_input_result(context: str, success_message: str, dry_run_message: str, result, args: argparse.Namespace) -> int:
    print(" ".join(result.command))
    if result.dry_run:
        print(dry_run_message)
        return 0
    if not result.ok:
        _print_adb_failure(context, result, adb_path=args.adb_path, serial=args.serial)
        return 1
    print(success_message)
    return 0


def _record_clicks(args: argparse.Namespace) -> int:
    print("Experimental live click recorder. It only writes YAML and never sends taps.")
    print("Click inside the target emulator window. Press Ctrl+C to stop.")
    clicks = run_windows_live_click_recorder(
        args.script,
        screenshot_path=args.screenshot,
        window_title=args.window_title,
        label_prefix=args.label_prefix,
        max_clicks=args.max_clicks,
    )
    print(f"Recorded {len(clicks)} click(s) into {args.script}.")
    return 0


def _ai_tool(args: argparse.Namespace) -> int:
    request_text = sys.stdin.read() if args.request == "-" else _read_text_file(args.request)
    request = json.loads(request_text)
    bridge = AiBridge.from_local_config(
        artifact_root=args.artifact_root,
        audit_path=args.audit_out,
        step_budget=args.step_budget,
        allow_device_input=args.allow_device_input,
        device_input_code=args.device_input_code,
        adb_path=args.adb_path,
        serial=args.serial,
    )
    response = bridge.handle(request)
    response_text = json.dumps(response, indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0 if response.get("ok") else 1


def _ai_server(args: argparse.Namespace) -> int:
    device_input_code = args.device_input_code
    if args.allow_device_input and not device_input_code:
        device_input_code = _generate_device_input_code()
    ready = create_ai_tool_server(
        AiToolServerConfig(
            host=args.host,
            port=args.port,
            artifact_root=Path(args.artifact_root),
            audit_path=Path(args.audit_out) if args.audit_out else None,
            step_budget=args.step_budget,
            allow_device_input=args.allow_device_input,
            device_input_code=device_input_code,
            adb_path=args.adb_path,
            serial=args.serial,
        )
    )
    print(f"AI tool server: {ready.url}")
    if args.allow_device_input:
        print("Real device input is enabled for this server session.")
        print(f"Device input code: {device_input_code}")
        print("Requests must include args.device_input_code with that value and args.execute=true.")
    else:
        print("Real device input is disabled; input tools remain dry-run.")
    print("POST JSON tool requests to /tool. Press Ctrl+C to stop.")
    try:
        ready.server.serve_forever()
    except KeyboardInterrupt:
        print("AI tool server stopped.")
    finally:
        ready.server.server_close()
    return 0


def _ai_schemas(args: argparse.Namespace) -> int:
    response_text = json.dumps(get_ai_schema_payload(), indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0


def _ai_examples(args: argparse.Namespace) -> int:
    response_text = json.dumps(get_ai_examples_payload(), indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0


def _ai_chat(args: argparse.Namespace) -> int:
    result = run_ai_chat(
        args.prompt,
        AiChatConfig(
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            temperature=args.temperature,
            timeout=args.timeout,
            max_tool_calls=args.max_tool_calls,
            allowed_tools=tuple(args.tool) if args.tool else None,
        ),
        bridge=AiBridge.from_local_config(
            artifact_root=args.artifact_root,
            audit_path=args.audit_out,
            step_budget=args.step_budget,
            allow_device_input=args.allow_device_input,
            device_input_code=args.device_input_code,
            adb_path=args.adb_path,
            serial=args.serial,
        ),
    )
    response_text = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.transcript_out:
        transcript_text = json.dumps({"ok": result.ok, "transcript": result.transcript or []}, indent=2, sort_keys=True) + "\n"
        _write_text_file(args.transcript_out, transcript_text)
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0 if result.ok else 1


def _ai_chat_smoke(args: argparse.Namespace) -> int:
    artifact_root = Path(args.artifact_root)
    script_root = artifact_root / "scripts"
    script_path = script_root / "ai-chat-smoke.yml"
    result = run_ai_chat(
        f"Smoke-test the provider chat tool loop by drafting a safe wait-only script. script:{script_path}",
        AiChatConfig(
            provider="fake",
            model="draft_script",
            max_tool_calls=1,
            allowed_tools=("draft_script", "validate"),
        ),
        bridge=AiBridge.from_local_config(
            artifact_root=artifact_root,
            audit_path=args.audit_out,
            step_budget=args.step_budget,
            allow_device_input=False,
            script_root=script_root,
        ),
    )
    response_text = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.transcript_out:
        transcript_text = json.dumps({"ok": result.ok, "transcript": result.transcript or []}, indent=2, sort_keys=True) + "\n"
        _write_text_file(args.transcript_out, transcript_text)
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0 if result.ok else 1


def _ai_adapter(args: argparse.Namespace) -> int:
    response_text = json.dumps(get_ai_adapter_payload(prefix_names=args.prefix_names), indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0


def _ai_mcp_stdio(args: argparse.Namespace) -> int:
    return run_mcp_stdio(
        McpStdioConfig(
            artifact_root=Path(args.artifact_root),
            audit_path=Path(args.audit_out) if args.audit_out else None,
            step_budget=args.step_budget,
            allow_device_input=args.allow_device_input,
            device_input_code=args.device_input_code,
            adb_path=args.adb_path,
            serial=args.serial,
        )
    )


def _ai_mcp_smoke(args: argparse.Namespace) -> int:
    result = run_ai_mcp_smoke(
        McpStdioConfig(
            artifact_root=Path(args.artifact_root),
            audit_path=Path(args.audit_out) if args.audit_out else None,
            step_budget=args.step_budget,
            allow_device_input=args.allow_device_input,
            device_input_code=args.device_input_code,
            adb_path=args.adb_path,
            serial=args.serial,
        ),
        example_name=args.example,
        allow_real_examples=args.allow_real_examples,
    )
    response_text = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0 if result.ok else 1


def _ai_smoke(args: argparse.Namespace) -> int:
    result = run_ai_client_smoke(
        base_url=args.base_url,
        example_name=args.example,
        timeout=args.timeout,
        allow_real_examples=args.allow_real_examples,
    )
    response_text = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.out:
        _write_text_file(args.out, response_text)
    else:
        print(response_text, end="")
    return 0 if result.ok else 1


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
        print("Agent run sent real tap and gesture steps.")
    else:
        print("Agent run kept tap and gesture steps dry-run.")
    print(f"Report: {summary.report_path}")
    print(f"Audit: {summary.audit_path}")
    return 0


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_text_file(path: str, text: str) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def _generate_device_input_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    chooser = random.SystemRandom()
    return "".join(chooser.choice(alphabet) for _ in range(length))


if __name__ == "__main__":
    raise SystemExit(main())
