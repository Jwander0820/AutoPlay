# Architecture

AutoPlay is a local-first controller for repeatable mobile game daily tasks. The current target is BlueStacks 5 controlled through ADB.

## Components

- CLI: `py -m autoplay doctor`, `py -m autoplay validate`, `py -m autoplay match`, `py -m autoplay screenshot`, `py -m autoplay tap`, and `py -m autoplay run`.
- ADB client: one wrapper around `subprocess.run()` that returns structured results.
- Core API: next-stage module that exposes typed Python functions for CLI, recorder, and AI tool calls.
- Script parser: YAML DSL v1 is parsed into typed step dataclasses.
- Validator: checks scripts before they can run against ADB.
- Image matcher: verifies PNG templates against screenshots for screen-state checkpoints.
- Runner: executes validated scripts with dry-run taps by default.
- Run report: records step events, ADB result summaries, and errors as JSON artifacts.

## Data flow

```text
YAML script -> parser -> validator -> runner -> ADB client -> BlueStacks
```

Next-stage flow:

```text
AI/tool UI/CLI -> core API -> validator/runner/ADB client -> BlueStacks
```

Screenshots are written to artifact paths declared by the script. Checkpoints can verify file existence or match a template image against a screenshot.

Run reports are optional JSON files written with `py -m autoplay run --report-out`. They are intended for user testing and post-run debugging.

## Safety posture

The project avoids semantic actions such as purchasing, gacha, trading, deleting items, PvP, chat, or bypassing anti-automation systems. The runner stops on validation errors, ADB failures, missing screenshots, and missing checkpoints.

AI-facing APIs must keep these same boundaries. Real device input should require explicit execution flags and should produce auditable reports.
