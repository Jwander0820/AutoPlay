# Next Stage Handoff

This file is the starting point for the next conversation.

## Goal

Move AutoPlay from a CLI proof of concept into a user-friendly script creation tool with a typed core API that AI agents can call safely.

## Current state

- BlueStacks ADB control works through `AdbClient`.
- CLI commands exist for doctor, screenshot, tap, run, validate, and match.
- YAML DSL supports screenshot, checkpoint_exists, checkpoint_match, wait, and tap.
- Runner validates scripts before execution and writes JSON reports with `--report-out`.
- Template matching is usable for exact/small-region checks, but full-screen fuzzy matching is intentionally bounded.
- Core CLI behavior is available through `src/autoplay/api.py` for Python callers and future AI/recorder tools.
- Guided script authoring is available through `py -m autoplay record <script.yml>`.
- AI-facing tool sessions are available through `src/autoplay/agent_tools.py` with step budgets, audit logs, dry-run defaults, and unsafe intent blocking.
- `py -m autoplay agent-run <script.yml>` runs scripts through the AI-facing safety session and writes both a runner report and an agent audit log.
- `py -m autoplay click-map <screenshot.png> --out <page.html>` creates a local browser UI for collecting tap coordinates from screenshots.
- `py -m autoplay record-ui <script.yml> --screenshot <screen.png>` starts a local recorder UI that saves YAML directly and validates it.
- `py -m autoplay record-clicks <script.yml>` experimentally records live Windows clicks inside a BlueStacks window into YAML tap steps.
- `record-ui` supports continuous capture and an explicit opt-in Tap + Wait + Capture loop for multi-screen flows.

## Proposed next feature

Continue improving the guided recorder command:

```powershell
py -m autoplay record scripts\my-daily.yml
```

The recorder currently:

1. Start from a YAML output path.
2. Offer commands such as `screenshot`, `tap X Y LABEL`, `wait SECONDS`, `checkpoint_exists PATH`, `done`.
3. Append steps to the YAML file after each accepted command.
4. Validate after each append.
5. Never send real taps during recording.

Future improvements should:

1. Add `checkpoint_match` authoring.
2. Optionally write a report or draft notes under `artifacts/`.
3. Improve prompts and recovery for validation errors.

## Core API direction

Create an internal API layer separate from CLI parsing. Suggested module:

```text
src/autoplay/api.py
```

Suggested functions:

- `doctor(adb_path=None, serial=None) -> DoctorReport`
- `screenshot(out, adb_path=None, serial=None) -> AdbResult`
- `tap(x, y, adb_path=None, serial=None, execute=False) -> AdbResult`
- `validate(script_path) -> ValidationReport`
- `run(script_path, execute_taps=False, report_out=None) -> RunnerReport`
- `match(source, template, threshold=0.95, tolerance=0, region=None) -> MatchResult`

AI-facing tools should call this API rather than shelling out to CLI commands.

## Safety rules for AI tool use

- Default all device input to dry-run.
- Require an explicit `execute=True` or equivalent for real taps.
- Require validation before running a YAML script.
- Store screenshots, templates, and reports under `artifacts/`.
- Preserve step budgets for any future agent loop.
- Do not support purchases, gacha, trading, deletion, chat, PvP, verification-code handling, anti-cheat bypass, root/hook/memory modification, or credential entry.

## Suggested specs

- `0005-guided-recorder.md`: interactive recorder for YAML authoring.
- `0006-core-api.md`: stable Python API for CLI and AI tool calls.
- `0007-agent-tool-safety.md`: bounded AI tool invocation rules and audit logs.

## First implementation slice

`0006-core-api.md` is implemented. CLI commands now call `autoplay.api`, which gives the recorder and future AI tools the same behavior as the CLI.

`0005-guided-recorder.md` is implemented as a thin interactive shell on top of the API and YAML parser/writer.

`0007-agent-tool-safety.md` is implemented for bounded AI tool invocation rules and audit logs.

`0008-agent-run-cli.md` is implemented as the first user-testable AI automation rail.

`0009-click-map-helper.md` is implemented for convenient coordinate capture from screenshots.

`0010-record-ui.md` is implemented for browser-based script recording with direct save and validation.

`0011-live-click-recorder.md` is experimental for Windows-only live click capture.

`0012-continuous-recorder-ui.md` is implemented for multi-screen record flows.

Next, test coordinate calibration on real BlueStacks, add template-cropping support, and build a first decision loop that uses screenshots and template matches to choose the next safe YAML/script step before any real tap execution.
