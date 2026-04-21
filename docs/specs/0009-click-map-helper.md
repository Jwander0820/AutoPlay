# 0009 Click Map Helper

## Status

Implemented.

## Summary

AutoPlay includes a lightweight local HTML script builder. It helps users build personal scripts by clicking on a screenshot and downloading a YAML script instead of manually guessing or backfilling tap coordinates.

## Behavior

- `py -m autoplay click-map <screenshot.png> --out <builder.html>` reads an existing screenshot and writes a self-contained HTML file.
- `py -m autoplay click-map <screenshot.png> --capture --out <builder.html>` captures a fresh screenshot through ADB before writing the HTML file.
- `--script-out <name.yml>` sets the default filename used by the HTML download button.
- The HTML embeds the screenshot as a data URI, so it can be opened directly in a browser without a local server.
- Clicking the screenshot records scaled source-image coordinates.
- The page displays:
  - editable script-step table
  - controls for wait, screenshot, checkpoint_exists, and checkpoint_match steps
  - recorder commands for supported recorder steps
  - complete YAML script output
  - copy buttons
  - a `Download Script` button

## Safety

- `click-map` only captures screenshots and writes an HTML helper.
- It never sends tap input.
- Real tap execution still requires `run --execute-taps`, `tap --yes`, or `agent-run --execute-taps --allow-device-input`.

## Acceptance

- Tests cover HTML generation, embedded screenshot output, script download filename configuration, capture-before-map behavior, failed screenshot handling, and CLI wiring.
