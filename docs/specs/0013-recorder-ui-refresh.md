# 0013 Recorder UI Refresh

## Status

Implemented.

## Summary

The browser recorder UI is refreshed into a Traditional Chinese recording workspace. The goal is to make script authoring feel closer to a guided workflow: inspect the current screen, click to record an action, decide how waits should be handled, capture the next screen, and keep the generated YAML visible.

## Behavior

- The UI uses Traditional Chinese labels for the main workflow, status messages, controls, timeline, and YAML output.
- The layout is organized as a two-column workspace:
  - current screenshot on the left
  - recording settings, helper steps, timeline, commands, and YAML on the right
- Click handling has two modes:
  - script-only mode records tap steps without touching the device
  - device mode, available only when `record-ui --allow-device-input` is used, sends a real tap and captures the next screenshot
- Wait handling has two modes:
  - manual mode uses the configured wait seconds
  - auto mode estimates waits from real recording time in script-only flows
- In device mode with auto wait enabled, the recorder waits after a tap until the screenshot changes and remains stable for a short period, or the configured maximum wait is reached, then records the measured wait and captured screenshot.
- The timeline stays editable by allowing recorded steps to be removed before saving.
- The UI can test the currently edited YAML through the same agent safety rail:
  - dry-run test never sends real taps
  - real test requires `record-ui --allow-device-input`
- When `record-ui` is launched with `--serial`, the generated YAML includes `profile.serial` so later runs target the same device.

## Safety

- Script-only mode remains the default.
- Device input still requires both the CLI opt-in flag and the browser-side device mode.
- Auto wait does not broaden what the tool may click; it only changes how long the recorder waits before capturing or writing a wait step.
- Generated scripts still need validation before they should be run.

## Acceptance

- Static click-map HTML includes the refreshed Chinese UI and still emits YAML.
- `record-ui` saves scripts and validates them through the existing `/api/script` endpoint.
- `record-ui` can dry-run the current script through `/api/run`.
- Tap capture still refuses device input unless explicitly enabled.
- Auto wait tap capture returns the measured wait metadata and a refreshed screenshot payload.
