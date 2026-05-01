from __future__ import annotations

from .script import MAX_GESTURE_DURATION_MS, MIN_GESTURE_DURATION_MS, VALID_SCROLL_DIRECTIONS, ScriptError


DEFAULT_SCROLL_DISTANCE = 700
DEFAULT_SCREEN_WIDTH = 1080
DEFAULT_SCREEN_HEIGHT = 1920
DEFAULT_SCROLL_CENTER_X = DEFAULT_SCREEN_WIDTH // 2
DEFAULT_SCROLL_CENTER_Y = DEFAULT_SCREEN_HEIGHT // 2


def compile_scroll(
    direction: str,
    distance: int | None = None,
    screen_width: int = DEFAULT_SCREEN_WIDTH,
    screen_height: int = DEFAULT_SCREEN_HEIGHT,
) -> tuple[int, int, int, int]:
    if direction not in VALID_SCROLL_DIRECTIONS:
        raise ScriptError("scroll direction must be one of: up, down, left, right.")
    resolved_distance = DEFAULT_SCROLL_DISTANCE if distance is None else distance
    if not isinstance(resolved_distance, int) or resolved_distance <= 0:
        raise ScriptError("scroll distance must be a positive integer.")
    if not isinstance(screen_width, int) or screen_width <= 0 or not isinstance(screen_height, int) or screen_height <= 0:
        raise ScriptError("scroll screen size must use positive integers.")

    center_x = screen_width // 2
    center_y = screen_height // 2
    half = resolved_distance // 2
    if direction == "up":
        return center_x, _clamp(center_y + half, screen_height), center_x, _clamp(center_y - half, screen_height)
    if direction == "down":
        return center_x, _clamp(center_y - half, screen_height), center_x, _clamp(center_y + half, screen_height)
    if direction == "left":
        return _clamp(center_x + half, screen_width), center_y, _clamp(center_x - half, screen_width), center_y
    return _clamp(center_x - half, screen_width), center_y, _clamp(center_x + half, screen_width), center_y


def _clamp(value: int, size: int) -> int:
    return max(0, min(size - 1, value))


def swipe_metadata(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int,
    dry_run: bool,
    label: str | None,
) -> dict[str, int | bool | str | None]:
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "duration_ms": duration_ms,
        "dry_run": dry_run,
        "label": label,
    }
