# 0019 - BlueStacks Gesture Calibration Profile

## Status

First implementation slice complete. Calibration profiles can be loaded for `record-ui`, surfaced in the UI, and used by device-mode scroll execution.

## Why

AutoPlay now supports direct gesture authoring and one-step gesture execution with wait-and-capture in `record-ui`, but gesture behavior still relies on conservative defaults:

- `scroll` compiles from a generic 1080x1920-centered assumption
- overlay previews assume the same screen geometry for every emulator profile
- user testing still has to "guess and retry" distances when a real BlueStacks layout differs from the default

That is good enough for unit-tested scaffolding, but not good enough for reliable daily automation on real devices and emulator profiles.

## Goals

- Introduce a calibration profile that captures real BlueStacks screen geometry and preferred gesture defaults.
- Let `scroll` and related recorder previews use calibrated values instead of a single hard-coded assumption.
- Keep calibration explicit, local, and reviewable rather than silently inferred.
- Preserve the current dry-run and validation-first safety model.

## Non-goals

- No autonomous calibration wizard in this slice.
- No cloud sync or shared profile registry.
- No per-app machine vision or heuristic screen classification.
- No unrestricted device loops.

## Proposed data shape

Calibration should live in a small local JSON file, for example:

```json
{
  "serial": "emulator-5554",
  "screen_width": 1080,
  "screen_height": 1920,
  "scroll_vertical_distance": 760,
  "scroll_horizontal_distance": 520,
  "default_swipe_duration_ms": 400,
  "default_drag_duration_ms": 700
}
```

Suggested path:

```text
artifacts/calibration/bluestacks-emulator-5554.json
```

## Scope

1. Add a lightweight calibration profile loader/saver.
2. Allow `record-ui` and future CLI helpers to read a calibration profile for the current serial.
3. Update `scroll` compilation and recorder preview overlays to prefer calibrated distances when available.
4. Keep current defaults as fallback when no profile exists.
5. Expose the active calibration summary in the recorder UI so users know which assumptions are in play.

## UX expectations

- Users can still record without calibration.
- When a calibration profile exists, the recorder UI should clearly show that calibrated values are active.
- Changing the target serial should naturally switch which calibration profile applies.
- If the serial is unknown or calibration is missing, the UI should stay usable and fall back to conservative defaults.

## Safety

- Calibration files must be local artifacts only.
- Loading a calibration profile must never imply real device input.
- Missing or malformed calibration files must degrade safely to defaults.

## Suggested implementation notes

- Put parsing and fallback logic in a small dedicated module rather than inside `click_map.py` or `recorder_server.py`.
- Keep the profile shape intentionally narrow so unit tests stay straightforward.
- Only add fields that affect current behavior; avoid speculative metadata.

## Open questions

- Should calibration be keyed only by `serial`, or by both `serial` and window/layout variant?
- Should the recorder UI include a tiny manual editor for calibration values, or should calibration remain file/CLI driven at first?
- Should `scroll` store the calibrated screen size in generated YAML metadata, or remain runtime-only behavior?

## First tests to add

- Loading a valid calibration profile applies custom scroll distances.
- Missing calibration profile falls back to existing defaults.
- Malformed calibration JSON is surfaced as a warning but does not break recorder startup.
- Recorder UI HTML reflects the active calibrated values when a profile is present.

## Implementation status

- Implemented: `src/autoplay/calibration.py` with typed profile loading, saving, default fallback, safe serial-based paths, and warning-preserving malformed-profile handling.
- Implemented: `record-ui` loads `artifacts/calibration/bluestacks-<serial>.json` when a serial is provided.
- Implemented: recorder UI shows active calibration status, screen size, and vertical/horizontal scroll distances.
- Implemented: device-mode scroll execution can use calibrated screen dimensions and calibrated distance when the UI step omits an explicit distance.
- Implemented: `py -m autoplay calibration write/show` can create and inspect local calibration profile JSON files.
- Implemented: `calibration write --from-screenshot <png>` can fill screen dimensions from an existing screenshot.
- Implemented: `calibration show --json` exposes machine-readable calibration state for future tools.
- Implemented: `py -m autoplay scroll --calibrated --serial ...` can use the same profile for CLI scroll dry-runs or real execution.
- Still pending: a guided calibration wizard that derives these values from real BlueStacks measurements instead of typed arguments.
