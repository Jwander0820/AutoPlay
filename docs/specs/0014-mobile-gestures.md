# 0014 Mobile Gestures

## Status

Implemented.

## Summary

AutoPlay needs mobile gesture primitives beyond tap so daily-task scripts can operate common Android and game UI flows. This spec adds swipe, drag, scroll, and back as first-class actions across ADB, API, YAML, runner, CLI, agent tools, and the recorder UI.

## Goals

- Simulate common phone actions safely and repeatably.
- Keep gesture execution dry-run by default.
- Preserve validation, reports, and audit logs for every gesture.
- Make gesture authoring simple in the Web UI.

## Step Types

### `swipe`

```yaml
- type: swipe
  x1: 500
  y1: 1400
  x2: 500
  y2: 500
  duration_ms: 500
  label: scroll daily list
```

Runs:

```text
adb shell input swipe X1 Y1 X2 Y2 DURATION_MS
```

### `drag`

```yaml
- type: drag
  x1: 300
  y1: 900
  x2: 800
  y2: 900
  duration_ms: 900
  label: move slider
```

Uses the same ADB primitive as swipe but remains a separate step type for readability, validation, reporting, and future UI authoring.

### `scroll`

```yaml
- type: scroll
  direction: down
  distance: 700
  duration_ms: 500
  label: scroll quest list
```

Compiles to a screen-relative swipe. Direction must be one of:

- `up`
- `down`
- `left`
- `right`

### `back`

```yaml
- type: back
  label: close reward panel
```

Runs:

```text
adb shell input keyevent BACK
```

## Validation

- Coordinates must be non-negative integers.
- `duration_ms` must be between `50` and `5000`.
- `scroll.direction` must be valid.
- `scroll.distance`, when provided, must be positive.
- Gesture labels should be present for reviewability.
- Unsafe labels should be blocked by the same intent rules used for taps.

## API

Add Python functions:

- `swipe(x1, y1, x2, y2, duration_ms=300, adb_path=None, serial=None, execute=False)`
- `drag(x1, y1, x2, y2, duration_ms=700, adb_path=None, serial=None, execute=False)`
- `scroll(direction, distance=None, duration_ms=400, adb_path=None, serial=None, execute=False)`
- `back(adb_path=None, serial=None, execute=False)`

All functions must default to dry-run.

## CLI

Add commands:

```powershell
py -m autoplay swipe 500 1400 500 500 --duration-ms 500
py -m autoplay drag 300 900 800 900 --duration-ms 900
py -m autoplay scroll down --distance 700 --duration-ms 500
py -m autoplay back
```

Real execution must require `--yes`, matching `tap`.

## Recorder UI

The Web UI adds a gesture section:

- scroll direction buttons
- distance and duration fields
- back button
- explicit coordinate fields for swipe/drag

Later pointer-drag capture can be added, but the first slice can be form-based.

## Implementation Notes

- `scroll` currently compiles to a conservative 1080x1920-centered swipe helper. Real BlueStacks calibration can refine this once tested against the target emulator window.
- The legacy `--execute-taps` flag and `dry_run_taps` report field are retained for compatibility, but now cover tap and gesture device input.
- Recorder UI gesture authoring writes YAML. Real execution still goes through the existing dry-run/real test path and requires `--allow-device-input`.

## Safety

- Gestures are device input and must follow the same dry-run and opt-in rules as taps.
- `agent-run` must audit gesture metadata.
- Recorder real-test mode must still require `--allow-device-input`.
- No gesture should bypass blocked intents such as purchases, gacha, trading, deletion, chat, PvP, verification-code handling, credential entry, anti-cheat bypass, root/hook, or memory modification.

## Acceptance

- Implemented: unit tests cover ADB command construction for swipe and back.
- Implemented: unit tests cover YAML parsing and validation for gesture steps.
- Implemented: runner reports dry-run gesture events with metadata.
- Implemented: CLI commands expose dry-run gesture testing.
- Implemented: core API exposes typed gesture functions.
- Implemented: agent tools audit gesture calls and block unsafe labels.
- Implemented: recorder UI can append `scroll`, `back`, `swipe`, and `drag` steps.
