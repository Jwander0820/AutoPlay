# 0006 Core API

## Status

Implemented.

## Summary

AutoPlay exposes a typed Python API so recorders and AI-facing tools can call the same core behavior as the CLI without shelling out. The CLI remains a thin argument and output layer over `autoplay.api`.

## Behavior

- `autoplay.api.doctor(adb_path=None, serial=None)` returns a `DoctorReport`.
- `autoplay.api.screenshot(out, adb_path=None, serial=None)` captures a PNG through ADB and returns an `AdbResult`.
- `autoplay.api.tap(x, y, adb_path=None, serial=None, execute=False)` returns an `AdbResult`; by default it is dry-run and does not send device input.
- `autoplay.api.validate(script_path)` returns a `ValidationReport`.
- `autoplay.api.run(script_path, execute_taps=False, report_out=None)` validates before execution, keeps tap steps dry-run by default, and writes a JSON report when requested.
- `autoplay.api.match(source, template, threshold=0.95, tolerance=0, region=None)` returns a `MatchResult` and accepts either a `Region` or `[x, y, width, height]`.

## Safety

- Device input requires explicit opt-in: `tap(..., execute=True)` or `run(..., execute_taps=True)`.
- YAML scripts are validated before the runner is invoked.
- Match thresholds, tolerances, and regions are bounded before image matching starts.
- Runner and matcher retain their existing limits for failed ADB calls, missing checkpoints, and overly large fuzzy searches.

## Acceptance

- CLI commands for doctor, screenshot, tap, run, validate, and match call `autoplay.api`.
- API tests cover tap dry-run defaults, explicit tap execution delegation, validation before run, report writing, region coercion, and bounded match parameters.
- Existing CLI, runner, validation, script, ADB, path, and image-match tests continue to pass.
