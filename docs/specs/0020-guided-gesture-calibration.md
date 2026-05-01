# 0020 - Guided Gesture Calibration

## Status

Draft for the next implementation slice.

## Why

The first calibration profile slice made gesture assumptions explicit and reusable:

- local JSON profiles can store screen dimensions and gesture defaults
- `record-ui` can show whether calibrated values are active
- CLI `scroll --calibrated` can use the same profile as the recorder

The missing piece is still user experience. A tester should not need to guess a scroll distance, edit JSON by hand, and retry until the gesture feels right. The next slice should guide the tester through a bounded calibration flow, keep every real device action opt-in, and produce a reviewable profile that improves both CLI and Web UI gesture behavior.

## Goals

- Add a guided calibration workflow that helps derive screen size and scroll defaults for one BlueStacks serial.
- Keep the workflow useful without requiring a full autonomous decision loop.
- Use existing screenshots and calibration profile files wherever possible.
- Record tester observations in local artifacts so calibration results are auditable.
- Feed the same profile back into `record-ui`, CLI `scroll --calibrated`, and later post-gesture checkpoint work.

## Non-goals

- No unrestricted loop that repeatedly swipes or taps without tester confirmation.
- No automatic game/task solving.
- No anti-cheat bypass, hooks, root access, memory reading, or emulator modification.
- No cloud sync for calibration profiles.
- No app-specific image recognition beyond existing screenshot/template primitives.

## Proposed UX

Start with a serial and screenshot:

```powershell
py -m autoplay calibration guide --serial emulator-5554 --from-screenshot artifacts\manual\start.png
```

The guide should:

1. Load the existing profile if present, otherwise start from screenshot dimensions and conservative defaults.
2. Show the current profile summary.
3. Offer dry-run preview commands for vertical and horizontal scroll.
4. Ask the tester to optionally run one real scroll with `--yes` or an explicit prompt confirmation.
5. Let the tester enter whether the movement was too short, okay, or too long.
6. Adjust the suggested distance in small bounded increments.
7. Save the final profile and a short calibration note under `artifacts/calibration/`.

The first implementation can be CLI-only. A later UI pass can surface the same workflow inside `record-ui`.

## Data

Continue using the 0019 profile shape:

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

Add optional local notes as a separate artifact so the executable profile stays narrow:

```text
artifacts/calibration/bluestacks-emulator-5554-notes.md
```

Suggested note content:

- timestamp
- serial
- screenshot path and dimensions
- tested directions
- final distances
- tester comments

## Scope

1. Add `calibration guide` as a bounded CLI workflow.
2. Reuse `CalibrationProfile`, `save_calibration_profile`, `read_png`, and `api.scroll`.
3. Keep all real device input behind explicit confirmation.
4. Write/update the profile JSON only after the tester confirms the final values.
5. Write a local markdown note with the decisions made during the session.
6. Add unit tests for non-interactive guide helpers and CLI validation.

## Safety

- The guide defaults to dry-run previews.
- Real scroll tests require `--yes` or a clear interactive confirmation.
- Each real test sends at most one scroll step before returning to the prompt.
- The guide must print the exact ADB command before real execution.
- Invalid profiles or screenshots should fail with clear errors, not partial writes.

## Record-UI Follow-Up

After the CLI workflow exists, `record-ui` should expose a small calibration entry point:

- show active profile status near the screenshot
- link or print the exact `calibration guide` command for the current serial/screenshot
- keep quick scroll buttons using calibrated vertical/horizontal defaults
- warn when the current screenshot dimensions differ from the loaded profile

## Acceptance Criteria

- A tester can create a useful calibration profile without manually editing JSON.
- Running the guide without `--yes` never sends device input.
- The saved profile is immediately visible through `py -m autoplay calibration show --serial ...`.
- `py -m autoplay scroll down --calibrated --serial ...` uses the saved vertical distance and screen dimensions.
- `record-ui` still works when calibration is absent, malformed, or incomplete.
- Unit tests cover profile loading, guide value adjustment, note writing, and CLI parser behavior.

## Open Questions

- Should the guide ask for "too short / okay / too long", or allow exact numeric entry first?
- Should calibration be separated by app orientation or BlueStacks window layout in addition to serial?
- Should future profiles store observed safe start/end points for scrolls, or keep only screen size and distance?
