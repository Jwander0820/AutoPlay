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
                "  wait SECONDS",
                "  checkpoint_exists PATH",
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
