from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import yaml

from . import api
from .script import ScriptError
from .validation import format_report


@dataclass(frozen=True)
class RecorderReport:
    script_path: Path
    appended_steps: int


def append_step_to_script(script_path: str | Path, step: dict) -> None:
    path = Path(script_path)
    data = _read_script_data(path)
    data["steps"].append(step)
    _write_script_data(path, data)


def record_script(script_path: str | Path, input_stream: TextIO, output_stream: TextIO) -> RecorderReport:
    path = Path(script_path)
    appended_steps = 0
    _print_intro(path, output_stream)

    while True:
        output_stream.write("record> ")
        output_stream.flush()
        line = input_stream.readline()
        if line == "":
            output_stream.write("\nEOF received; recording stopped.\n")
            break

        raw_command = line.strip()
        if not raw_command:
            continue
        if raw_command in {"done", "exit", "quit"}:
            output_stream.write("Recording complete.\n")
            break
        if raw_command in {"help", "?"}:
            _print_help(output_stream)
            continue

        try:
            step = parse_record_command(raw_command)
        except ScriptError as exc:
            output_stream.write(f"ERROR: {exc}\n")
            continue

        append_step_to_script(path, step)
        appended_steps += 1
        output_stream.write(f"Appended: {step['type']}\n")
        _print_validation(path, output_stream)

    return RecorderReport(script_path=path, appended_steps=appended_steps)


def parse_record_command(raw_command: str) -> dict:
    try:
        parts = shlex.split(raw_command)
    except ValueError as exc:
        raise ScriptError(f"Invalid command syntax: {exc}") from exc
    if not parts:
        raise ScriptError("Command is empty.")

    command = parts[0]
    args = parts[1:]
    if command == "screenshot":
        _require_arg_count(command, args, 1)
        return {"type": "screenshot", "out": args[0]}
    if command == "checkpoint_exists":
        _require_arg_count(command, args, 1)
        return {"type": "checkpoint_exists", "path": args[0]}
    if command == "checkpoint_match":
        return _parse_checkpoint_match(args)
    if command == "wait":
        _require_arg_count(command, args, 1)
        return {"type": "wait", "seconds": _parse_seconds(args[0])}
    if command == "tap":
        if len(args) < 3:
            raise ScriptError("tap usage: tap X Y LABEL")
        return {
            "type": "tap",
            "x": _parse_coordinate(args[0], "x"),
            "y": _parse_coordinate(args[1], "y"),
            "label": " ".join(args[2:]),
        }
    if command in {"swipe", "drag"}:
        if len(args) < 6:
            raise ScriptError(f"{command} usage: {command} X1 Y1 X2 Y2 DURATION_MS LABEL")
        return {
            "type": command,
            "x1": _parse_coordinate(args[0], "x1"),
            "y1": _parse_coordinate(args[1], "y1"),
            "x2": _parse_coordinate(args[2], "x2"),
            "y2": _parse_coordinate(args[3], "y2"),
            "duration_ms": _parse_duration_ms(args[4], command),
            "label": " ".join(args[5:]),
        }
    if command == "scroll":
        if len(args) < 2:
            raise ScriptError("scroll usage: scroll DIRECTION [DISTANCE] [DURATION_MS] LABEL")
        step = {"type": "scroll", "direction": _parse_direction(args[0])}
        label_start = 1
        if len(args) > label_start and _looks_int(args[label_start]):
            step["distance"] = _parse_positive_int(args[label_start], "scroll distance")
            label_start += 1
        if len(args) > label_start and _looks_int(args[label_start]):
            step["duration_ms"] = _parse_duration_ms(args[label_start], "scroll")
            label_start += 1
        label = " ".join(args[label_start:])
        if not label:
            raise ScriptError("scroll usage: scroll DIRECTION [DISTANCE] [DURATION_MS] LABEL")
        step["label"] = label
        return step
    if command == "back":
        if not args:
            raise ScriptError("back usage: back LABEL")
        return {"type": "back", "label": " ".join(args)}

    raise ScriptError(f"Unknown recorder command: {command}")


def _print_intro(path: Path, output_stream: TextIO) -> None:
    output_stream.write(f"Recording script: {path}\n")
    output_stream.write("Type help for commands, done to finish. Tap commands only write YAML; they never send input.\n")


def _print_help(output_stream: TextIO) -> None:
    output_stream.write(
        "\n".join(
            [
                "Commands:",
                "  screenshot PATH",
                "  tap X Y LABEL",
                "  swipe X1 Y1 X2 Y2 DURATION_MS LABEL",
                "  drag X1 Y1 X2 Y2 DURATION_MS LABEL",
                "  scroll DIRECTION [DISTANCE] [DURATION_MS] LABEL",
                "  back LABEL",
                "  wait SECONDS",
                "  checkpoint_exists PATH",
                "  checkpoint_match SOURCE TEMPLATE [THRESHOLD] [TOLERANCE] [REGION_X REGION_Y REGION_WIDTH REGION_HEIGHT]",
                "  done",
            ]
        )
        + "\n"
    )


def _print_validation(path: Path, output_stream: TextIO) -> None:
    report = api.validate(path)
    for line in format_report(report):
        output_stream.write(f"{line}\n")


def _read_script_data(path: Path) -> dict:
    if not path.exists():
        return {"steps": []}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScriptError(f"Invalid YAML: {exc}") from exc
    except OSError as exc:
        raise ScriptError(f"Cannot read script: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ScriptError("Script must be a YAML mapping.")
    raw_steps = data.setdefault("steps", [])
    if not isinstance(raw_steps, list):
        raise ScriptError("Script must contain a 'steps' list.")
    return data


def _write_script_data(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _require_arg_count(command: str, args: list[str], expected: int) -> None:
    if len(args) != expected:
        raise ScriptError(f"{command} usage: {command} {' '.join(_usage_names(command))}")


def _usage_names(command: str) -> list[str]:
    return {
        "screenshot": ["PATH"],
        "checkpoint_exists": ["PATH"],
        "checkpoint_match": ["SOURCE", "TEMPLATE", "[THRESHOLD]", "[TOLERANCE]", "[REGION_X", "REGION_Y", "REGION_WIDTH", "REGION_HEIGHT]"],
        "wait": ["SECONDS"],
    }.get(command, [])


def _parse_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise ScriptError("wait seconds must be a non-negative number.") from exc
    if seconds < 0:
        raise ScriptError("wait seconds must be a non-negative number.")
    return seconds


def _parse_coordinate(value: str, name: str) -> int:
    try:
        coordinate = int(value)
    except ValueError as exc:
        raise ScriptError(f"tap {name} must be a non-negative integer.") from exc
    if coordinate < 0:
        raise ScriptError(f"tap {name} must be a non-negative integer.")
    return coordinate


def _parse_checkpoint_match(args: list[str]) -> dict:
    if len(args) not in {2, 3, 4, 8}:
        raise ScriptError(
            "checkpoint_match usage: checkpoint_match SOURCE TEMPLATE [THRESHOLD] [TOLERANCE] [REGION_X REGION_Y REGION_WIDTH REGION_HEIGHT]"
        )
    step: dict = {"type": "checkpoint_match", "source": args[0], "template": args[1]}
    if len(args) >= 3:
        step["threshold"] = _parse_threshold(args[2])
    if len(args) >= 4:
        step["tolerance"] = _parse_tolerance(args[3])
    if len(args) == 8:
        step["region"] = _parse_region_args(args[4:8])
    return step


def _parse_threshold(value: str) -> float:
    try:
        threshold = float(value)
    except ValueError as exc:
        raise ScriptError("checkpoint_match threshold must be between 0 and 1.") from exc
    if threshold < 0 or threshold > 1:
        raise ScriptError("checkpoint_match threshold must be between 0 and 1.")
    return threshold


def _parse_tolerance(value: str) -> int:
    try:
        tolerance = int(value)
    except ValueError as exc:
        raise ScriptError("checkpoint_match tolerance must be an integer from 0 to 255.") from exc
    if tolerance < 0 or tolerance > 255:
        raise ScriptError("checkpoint_match tolerance must be an integer from 0 to 255.")
    return tolerance


def _parse_region_args(values: list[str]) -> list[int]:
    try:
        x, y, width, height = (int(value) for value in values)
    except ValueError as exc:
        raise ScriptError("checkpoint_match region must contain four integers.") from exc
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ScriptError("checkpoint_match region must use non-negative x/y and positive width/height.")
    return [x, y, width, height]


def _parse_duration_ms(value: str, command: str) -> int:
    duration = _parse_positive_int(value, f"{command} duration_ms")
    if duration < 50 or duration > 5000:
        raise ScriptError(f"{command} duration_ms must be between 50 and 5000.")
    return duration


def _parse_direction(value: str) -> str:
    if value not in {"up", "down", "left", "right"}:
        raise ScriptError("scroll direction must be one of: up, down, left, right.")
    return value


def _parse_positive_int(value: str, description: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ScriptError(f"{description} must be a positive integer.") from exc
    if number <= 0:
        raise ScriptError(f"{description} must be a positive integer.")
    return number


def _looks_int(value: str) -> bool:
    return value.isdecimal()
