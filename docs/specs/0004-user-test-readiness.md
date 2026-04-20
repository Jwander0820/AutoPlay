# 0004 User Test Readiness

## Status

Implemented.

## Summary

Before real user testing, AutoPlay must produce artifacts that help diagnose what happened during a run. Users should be able to validate a script, run it in dry-run mode, and preserve a JSON report for iteration.

## Behavior

- `py -m autoplay run <script.yml> --report-out <path>` writes a JSON report on successful runs.
- When the runner fails after execution starts, `--report-out` writes partial progress, events, ADB result summaries, and the error.
- Report files include status, start/end timestamps, dry-run state, executed step summaries, per-step events, and ADB command result summaries.
- `py -m autoplay run` still keeps tap steps dry-run by default.
- `examples/report-only.yml` provides a no-ADB report smoke test for environment checks.

## Acceptance

- Runner tests cover successful report serialization and failure reports carried by `RunnerError`.
- CLI tests cover writing `--report-out` for a script that does not require ADB.
- User testing docs explain the Windows smoke-test sequence and which artifacts to collect.
