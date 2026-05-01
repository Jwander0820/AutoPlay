from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ScriptError(ValueError):
    pass


@dataclass(frozen=True)
class TapStep:
    x: int
    y: int
    label: str | None = None


@dataclass(frozen=True)
class SwipeStep:
    x1: int
    y1: int
    x2: int
    y2: int
    duration_ms: int = 300
    label: str | None = None


@dataclass(frozen=True)
class DragStep:
    x1: int
    y1: int
    x2: int
    y2: int
    duration_ms: int = 700
    label: str | None = None


@dataclass(frozen=True)
class ScrollStep:
    direction: str
    distance: int | None = None
    duration_ms: int = 400
    label: str | None = None


@dataclass(frozen=True)
class BackStep:
    label: str | None = None


@dataclass(frozen=True)
class WaitStep:
    seconds: float


@dataclass(frozen=True)
class ScreenshotStep:
    out: Path


@dataclass(frozen=True)
class CheckpointExistsStep:
    path: Path


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class CheckpointMatchStep:
    source: Path
    template: Path
    threshold: float = 0.95
    tolerance: int = 0
    region: Region | None = None


Step = TapStep | SwipeStep | DragStep | ScrollStep | BackStep | WaitStep | ScreenshotStep | CheckpointExistsStep | CheckpointMatchStep


MIN_GESTURE_DURATION_MS = 50
MAX_GESTURE_DURATION_MS = 5000
VALID_SCROLL_DIRECTIONS = {"up", "down", "left", "right"}


@dataclass(frozen=True)
class ScriptProfile:
    adb_path: str | None = None
    serial: str | None = None


@dataclass(frozen=True)
class AutoplayScript:
    profile: ScriptProfile
    steps: list[Step]
    source_path: Path


def load_script(path: str | Path) -> AutoplayScript:
    source_path = Path(path)
    try:
        data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScriptError(f"Invalid YAML: {exc}") from exc
    except OSError as exc:
        raise ScriptError(f"Cannot read script: {exc}") from exc

    if not isinstance(data, dict):
        raise ScriptError("Script must be a YAML mapping.")

    profile = _parse_profile(data.get("profile", {}))
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raise ScriptError("Script must contain a 'steps' list.")
    if not raw_steps:
        raise ScriptError("Script must contain at least one step.")

    base_dir = source_path.parent
    steps = [_parse_step(raw_step, base_dir) for raw_step in raw_steps]
    return AutoplayScript(profile=profile, steps=steps, source_path=source_path)


def _parse_profile(raw_profile: Any) -> ScriptProfile:
    if raw_profile is None:
        return ScriptProfile()
    if not isinstance(raw_profile, dict):
        raise ScriptError("'profile' must be a mapping.")
    adb_path = raw_profile.get("adb_path")
    serial = raw_profile.get("serial")
    if adb_path is not None and not isinstance(adb_path, str):
        raise ScriptError("'profile.adb_path' must be a string.")
    if serial is not None and not isinstance(serial, str):
        raise ScriptError("'profile.serial' must be a string.")
    return ScriptProfile(adb_path=adb_path, serial=serial)


def _parse_step(raw_step: Any, base_dir: Path) -> Step:
    if not isinstance(raw_step, dict):
        raise ScriptError("Each step must be a mapping.")
    step_type = raw_step.get("type")
    if not isinstance(step_type, str):
        raise ScriptError("Each step must include a string 'type'.")

    if step_type == "wait":
        seconds = raw_step.get("seconds")
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise ScriptError("'wait.seconds' must be a non-negative number.")
        return WaitStep(seconds=float(seconds))

    if step_type == "tap":
        x = raw_step.get("x")
        y = raw_step.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise ScriptError("'tap.x' and 'tap.y' must be integers.")
        if x < 0 or y < 0:
            raise ScriptError("'tap.x' and 'tap.y' must be non-negative.")
        label = raw_step.get("label")
        if label is not None and not isinstance(label, str):
            raise ScriptError("'tap.label' must be a string.")
        return TapStep(x=x, y=y, label=label)

    if step_type in {"swipe", "drag"}:
        x1 = _parse_coordinate_field(raw_step, step_type, "x1")
        y1 = _parse_coordinate_field(raw_step, step_type, "y1")
        x2 = _parse_coordinate_field(raw_step, step_type, "x2")
        y2 = _parse_coordinate_field(raw_step, step_type, "y2")
        default_duration = 300 if step_type == "swipe" else 700
        duration_ms = _parse_duration_ms(raw_step.get("duration_ms", default_duration), step_type)
        label = _parse_optional_label(raw_step, step_type)
        if step_type == "swipe":
            return SwipeStep(x1=x1, y1=y1, x2=x2, y2=y2, duration_ms=duration_ms, label=label)
        return DragStep(x1=x1, y1=y1, x2=x2, y2=y2, duration_ms=duration_ms, label=label)

    if step_type == "scroll":
        direction = raw_step.get("direction")
        if direction not in VALID_SCROLL_DIRECTIONS:
            raise ScriptError("'scroll.direction' must be one of: up, down, left, right.")
        distance = raw_step.get("distance")
        if distance is not None:
            if not isinstance(distance, int):
                raise ScriptError("'scroll.distance' must be a positive integer.")
            if distance <= 0:
                raise ScriptError("'scroll.distance' must be positive.")
        duration_ms = _parse_duration_ms(raw_step.get("duration_ms", 400), "scroll")
        label = _parse_optional_label(raw_step, "scroll")
        return ScrollStep(direction=direction, distance=distance, duration_ms=duration_ms, label=label)

    if step_type == "back":
        label = _parse_optional_label(raw_step, "back")
        return BackStep(label=label)

    if step_type == "screenshot":
        out = raw_step.get("out")
        if not isinstance(out, str):
            raise ScriptError("'screenshot.out' must be a string.")
        return ScreenshotStep(out=_resolve_script_path(base_dir, out))

    if step_type == "checkpoint_exists":
        path = raw_step.get("path")
        if not isinstance(path, str):
            raise ScriptError("'checkpoint_exists.path' must be a string.")
        return CheckpointExistsStep(path=_resolve_script_path(base_dir, path))

    if step_type == "checkpoint_match":
        source = raw_step.get("source")
        template = raw_step.get("template")
        if not isinstance(source, str):
            raise ScriptError("'checkpoint_match.source' must be a string.")
        if not isinstance(template, str):
            raise ScriptError("'checkpoint_match.template' must be a string.")
        threshold = _parse_threshold(raw_step.get("threshold", 0.95))
        tolerance = _parse_tolerance(raw_step.get("tolerance", 0))
        region = _parse_region(raw_step.get("region"))
        return CheckpointMatchStep(
            source=_resolve_script_path(base_dir, source),
            template=_resolve_script_path(base_dir, template),
            threshold=threshold,
            tolerance=tolerance,
            region=region,
        )

    raise ScriptError(f"Unknown step type: {step_type}")


def _resolve_script_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def _parse_threshold(value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise ScriptError("'checkpoint_match.threshold' must be a number.")
    threshold = float(value)
    if threshold < 0 or threshold > 1:
        raise ScriptError("'checkpoint_match.threshold' must be between 0 and 1.")
    return threshold


def _parse_tolerance(value: Any) -> int:
    if not isinstance(value, int):
        raise ScriptError("'checkpoint_match.tolerance' must be an integer.")
    if value < 0 or value > 255:
        raise ScriptError("'checkpoint_match.tolerance' must be between 0 and 255.")
    return value


def _parse_coordinate_field(raw_step: dict, step_type: str, name: str) -> int:
    value = raw_step.get(name)
    if not isinstance(value, int):
        raise ScriptError(f"'{step_type}.{name}' must be an integer.")
    if value < 0:
        raise ScriptError(f"'{step_type}.{name}' must be non-negative.")
    return value


def _parse_duration_ms(value: Any, step_type: str) -> int:
    if not isinstance(value, int):
        raise ScriptError(f"'{step_type}.duration_ms' must be an integer.")
    if value < MIN_GESTURE_DURATION_MS or value > MAX_GESTURE_DURATION_MS:
        raise ScriptError(
            f"'{step_type}.duration_ms' must be between {MIN_GESTURE_DURATION_MS} and {MAX_GESTURE_DURATION_MS}."
        )
    return value


def _parse_optional_label(raw_step: dict, step_type: str) -> str | None:
    label = raw_step.get("label")
    if label is not None and not isinstance(label, str):
        raise ScriptError(f"'{step_type}.label' must be a string.")
    return label


def _parse_region(value: Any) -> Region | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(part, int) for part in value):
        raise ScriptError("'checkpoint_match.region' must be a list of four integers: [x, y, width, height].")
    x, y, width, height = value
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ScriptError("'checkpoint_match.region' must use non-negative x/y and positive width/height.")
    return Region(x=x, y=y, width=width, height=height)
