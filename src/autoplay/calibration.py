from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .gestures import DEFAULT_SCROLL_DISTANCE, DEFAULT_SCREEN_HEIGHT, DEFAULT_SCREEN_WIDTH
from .script import MAX_GESTURE_DURATION_MS, MIN_GESTURE_DURATION_MS, ScriptError


DEFAULT_SWIPE_DURATION_MS = 400
DEFAULT_DRAG_DURATION_MS = 700


@dataclass(frozen=True)
class CalibrationProfile:
    serial: str | None = None
    screen_width: int = DEFAULT_SCREEN_WIDTH
    screen_height: int = DEFAULT_SCREEN_HEIGHT
    scroll_vertical_distance: int = DEFAULT_SCROLL_DISTANCE
    scroll_horizontal_distance: int = DEFAULT_SCROLL_DISTANCE
    default_swipe_duration_ms: int = DEFAULT_SWIPE_DURATION_MS
    default_drag_duration_ms: int = DEFAULT_DRAG_DURATION_MS

    def __post_init__(self) -> None:
        _optional_string(self.serial)
        _positive_int(self.screen_width, "screen_width")
        _positive_int(self.screen_height, "screen_height")
        _positive_int(self.scroll_vertical_distance, "scroll_vertical_distance")
        _positive_int(self.scroll_horizontal_distance, "scroll_horizontal_distance")
        _duration_int(self.default_swipe_duration_ms, "default_swipe_duration_ms")
        _duration_int(self.default_drag_duration_ms, "default_drag_duration_ms")

    @property
    def source_label(self) -> str:
        return self.serial or "default"

    def distance_for_direction(self, direction: str) -> int:
        if direction in {"left", "right"}:
            return self.scroll_horizontal_distance
        return self.scroll_vertical_distance

    def to_dict(self) -> dict:
        return {
            "serial": self.serial,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "scroll_vertical_distance": self.scroll_vertical_distance,
            "scroll_horizontal_distance": self.scroll_horizontal_distance,
            "default_swipe_duration_ms": self.default_swipe_duration_ms,
            "default_drag_duration_ms": self.default_drag_duration_ms,
        }


@dataclass(frozen=True)
class CalibrationLoadResult:
    profile: CalibrationProfile
    path: Path | None = None
    loaded: bool = False
    warnings: tuple[str, ...] = ()

    def to_ui_dict(self) -> dict:
        data = self.profile.to_dict()
        data.update(
            {
                "loaded": self.loaded,
                "path": self.path.as_posix() if self.path is not None else None,
                "warnings": list(self.warnings),
            }
        )
        return data


def calibration_path_for_serial(artifact_root: str | Path, serial: str | None) -> Path:
    name = _safe_serial_name(serial)
    return Path(artifact_root) / "calibration" / f"bluestacks-{name}.json"


def load_calibration_for_serial(serial: str | None, artifact_root: str | Path = "artifacts") -> CalibrationLoadResult:
    path = calibration_path_for_serial(artifact_root, serial)
    if not path.exists():
        return CalibrationLoadResult(profile=CalibrationProfile(serial=serial), path=path)
    try:
        return CalibrationLoadResult(profile=load_calibration_profile(path), path=path, loaded=True)
    except (OSError, ScriptError, json.JSONDecodeError) as exc:
        return CalibrationLoadResult(profile=CalibrationProfile(serial=serial), path=path, warnings=(f"Cannot load calibration profile: {exc}",))


def load_calibration_profile(path: str | Path) -> CalibrationProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ScriptError("Calibration profile must be a JSON object.")
    return CalibrationProfile(
        serial=_optional_string(data.get("serial")),
        screen_width=_positive_int(data.get("screen_width", DEFAULT_SCREEN_WIDTH), "screen_width"),
        screen_height=_positive_int(data.get("screen_height", DEFAULT_SCREEN_HEIGHT), "screen_height"),
        scroll_vertical_distance=_positive_int(data.get("scroll_vertical_distance", DEFAULT_SCROLL_DISTANCE), "scroll_vertical_distance"),
        scroll_horizontal_distance=_positive_int(data.get("scroll_horizontal_distance", DEFAULT_SCROLL_DISTANCE), "scroll_horizontal_distance"),
        default_swipe_duration_ms=_duration_int(data.get("default_swipe_duration_ms", DEFAULT_SWIPE_DURATION_MS), "default_swipe_duration_ms"),
        default_drag_duration_ms=_duration_int(data.get("default_drag_duration_ms", DEFAULT_DRAG_DURATION_MS), "default_drag_duration_ms"),
    )


def save_calibration_profile(profile: CalibrationProfile, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _safe_serial_name(serial: str | None) -> str:
    if not serial:
        return "default"
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", serial).strip("-") or "default"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ScriptError("serial must be a string.")
    return value


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ScriptError(f"{name} must be a positive integer.")
    return value


def _duration_int(value: object, name: str) -> int:
    resolved = _positive_int(value, name)
    if resolved < MIN_GESTURE_DURATION_MS or resolved > MAX_GESTURE_DURATION_MS:
        raise ScriptError(f"{name} must be between {MIN_GESTURE_DURATION_MS} and {MAX_GESTURE_DURATION_MS}.")
    return resolved
