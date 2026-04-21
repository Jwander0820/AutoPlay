# 0012 Continuous Recorder UI

## Status

Implemented.

## Summary

The browser recorder now supports a continuous workflow: capture the current screen, add or execute an action, wait for the UI to settle, capture the next screen, and continue recording from the refreshed screenshot.

## Behavior

- `record-ui` exposes a `Capture Latest` button that captures a fresh screenshot and updates the browser image.
- Captures are saved beside the initial screenshot with numbered filenames such as `start-001.png`.
- The capture response appends a `screenshot` step to the in-browser script.
- `record-ui --allow-device-input` enables an explicit browser checkbox: `Execute click, wait, and capture next screen`.
- When enabled, clicking the screenshot sends a real tap, waits for the configured wait duration, captures the next screenshot, refreshes the image, and appends:
  - `tap`
  - optional `wait`
  - `screenshot`
- Without `--allow-device-input`, clicks only add tap steps and never touch the device.

## Safety

- Device input remains disabled by default.
- Real tap execution requires the CLI flag `--allow-device-input` and the browser checkbox.
- The recorder UI still only writes YAML and captures screenshots; real script execution remains separate through `run` or `agent-run`.

## Acceptance

- Tests cover capture refresh responses, tap-capture blocking without opt-in, tap-capture execution with opt-in, returned screenshot steps, and CLI propagation of the device-input flag.
