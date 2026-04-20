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
- There is no recorder yet. Personal scripts are currently semi-manual.

## Proposed next feature

Implement a guided recorder command:

```powershell
py -m autoplay record scripts\my-daily.yml
```

The recorder should:

1. Start from a YAML output path.
2. Offer commands such as `screenshot`, `tap X Y LABEL`, `wait SECONDS`, `checkpoint_exists PATH`, `done`.
3. Append steps to the YAML file after each accepted command.
4. Validate after each append.
5. Optionally write a report or draft notes under `artifacts/`.
6. Never send real taps during recording unless a future explicit flag is added.

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

Start with `0006-core-api.md`, then refactor CLI to call `autoplay.api`. This makes the recorder and future AI tools share the same behavior as the CLI.

After that, implement `record` as a thin interactive shell on top of the API and YAML parser/writer.
