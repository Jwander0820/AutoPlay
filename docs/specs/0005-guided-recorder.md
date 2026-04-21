# 0005 Guided Recorder

## Status

Implemented.

## Summary

AutoPlay includes a guided `record` command that helps users author YAML scripts by appending validated steps interactively. The first version records intent into a script file; it does not send tap input to the device.

## Behavior

- `py -m autoplay record <script.yml>` starts an interactive prompt.
- If the script file does not exist, the recorder creates it on the first accepted command.
- If the script file exists, existing top-level fields such as `profile` are preserved and new steps are appended to `steps`.
- Supported commands:
  - `screenshot PATH`
  - `tap X Y LABEL`
  - `wait SECONDS`
  - `checkpoint_exists PATH`
  - `help`
  - `done`
- After each accepted step, the recorder writes the YAML file and runs validation.
- Validation output is printed after each append so the user can immediately see warnings or errors.

## Safety

- `tap` commands only append YAML. The recorder never calls `autoplay.api.tap` and never sends real tap input.
- Coordinates and wait durations are rejected if negative.
- Labels are required for tap steps to encourage auditable scripts.
- Unknown commands are rejected and do not modify the YAML file.

## Acceptance

- Recorder tests cover command parsing, appending steps, preserving existing profile data, validation after appends, and no tap execution.
- CLI exposes `record` as a top-level subcommand.
