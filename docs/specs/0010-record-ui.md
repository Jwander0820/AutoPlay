# 0010 Record UI

## Status

Implemented.

## Summary

AutoPlay includes a local browser recorder that can save generated YAML directly to a script path. This upgrades the previous static script builder from "download and move a file" to "record, save, and validate in place."

## Behavior

- `py -m autoplay record-ui <script.yml> --screenshot <screen.png>` starts a local server on `127.0.0.1:8765` by default.
- `--capture` captures the screenshot through ADB before starting the server.
- The server renders the same script-builder UI as `click-map`.
- The browser UI can add tap, wait, screenshot, checkpoint_exists, and checkpoint_match steps.
- The `Save Script` button posts the complete YAML back to the local server.
- The server writes the YAML to the requested script path and returns validation messages.
- `Ctrl+C` stops the recorder server.

## Safety

- `record-ui` only captures screenshots and writes YAML.
- It never sends tap input.
- Real tap execution still requires `run --execute-taps`, `tap --yes`, or `agent-run --execute-taps --allow-device-input`.
- The server binds to localhost by default.

## Acceptance

- Tests cover serving the builder, saving valid YAML, surfacing validation errors, and CLI startup/shutdown wiring.
