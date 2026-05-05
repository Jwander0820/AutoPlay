# Next Stage Handoff

This file is the starting point for the next conversation.

## Goal

Move AutoPlay from a CLI proof of concept into a user-friendly script creation tool with a typed core API that AI agents can call safely.

Longer term, AutoPlay should support local AI conversation: the user can talk to a local AI assistant, the AI can inspect screenshots and call bounded AutoPlay tools, and real emulator input remains opt-in, audited, and reversible through reviewable YAML. The architecture direction is captured in `docs/ai-local-automation-plan.md`.

## Current state

- Android emulator ADB control works through `AdbClient`; BlueStacks and LDPlayer use the same core API surface.
- CLI commands exist for doctor, screenshot, tap, swipe, drag, scroll, back, calibration, run, validate, and match.
- YAML DSL supports screenshot, checkpoint_exists, checkpoint_match, wait, tap, swipe, drag, scroll, and back.
- Runner validates scripts before execution and writes JSON reports with `--report-out`.
- Template matching is usable for exact/small-region checks, but full-screen fuzzy matching is intentionally bounded.
- Core CLI behavior is available through `src/autoplay/api.py` for Python callers and future AI/recorder tools.
- Guided script authoring is available through `py -m autoplay record <script.yml>`.
- AI-facing tool sessions are available through `src/autoplay/agent_tools.py` with step budgets, audit logs, dry-run defaults, and unsafe intent blocking.
- `py -m autoplay agent-run <script.yml>` runs scripts through the AI-facing safety session and writes both a runner report and an agent audit log.
- `py -m autoplay click-map <screenshot.png> --out <page.html>` creates a local browser UI for collecting tap coordinates from screenshots.
- `py -m autoplay record-ui <script.yml> --screenshot <screen.png>` starts a local recorder UI that saves YAML directly and validates it.
- `py -m autoplay record-clicks <script.yml>` experimentally records live Windows clicks inside a matching emulator window into YAML tap steps.
- `record-ui` supports continuous capture and an explicit opt-in Tap + Wait + Capture loop for multi-screen flows.
- `record-ui` has a Traditional Chinese workspace UI with script-only/device modes, manual/auto wait modes, direct canvas gesture tools, visible calibration status, dry-run/real script test buttons, profile serial preservation, and auto wait-until-screen-stable support for tap and gesture capture.
- `record-ui` now surfaces execution context and a four-step workflow rail so testers can see connection, capture, recording, and validation state at a glance.
- Mobile gesture primitives are implemented across ADB, API, YAML, validation, runner, CLI, agent tools, guided recorder, and record-ui: `swipe`, `drag`, `scroll`, and `back`.

## Stage checkpoint

The current handoff point is after specs `0014` through `0019`:

- Gesture primitives are implemented across the project and covered by unit tests.
- `record-ui` can directly author gestures on the screenshot canvas and can execute one tap/gesture with wait-and-capture when launched with `--allow-device-input`.
- Template cropping can append `checkpoint_match`, so user tests can start moving from coordinate-only scripts toward checkpoint-first flows.
- Calibration profile support exists through both manual `calibration write/show` and guided `calibration guide`, plus `scroll --calibrated`, serial-aware profile loading, and Web UI calibration visibility.
- `calibration guide` is now available as a CLI-first workflow for deriving scroll distances from tester feedback, saving profile JSON, and writing local notes.
- `record-ui` shows the matching `calibration guide` command when serial context is available.
- `record-ui` now nudges testers into Template mode after device tap/gesture capture so post-action checkpoints are harder to forget.
- `docs/stage-report.md` contains the latest stage report, including verification commands and real emulator follow-up.

For the next commit or handoff, keep generated screenshots, calibration outputs, reports, audit logs, and personal scripts local under ignored paths such as `artifacts/` and `scripts/`.

## Proposed next feature

Use the new guided calibration workflow on the active real emulator profile, then use those findings to harden recorder gesture behavior and post-gesture verification. The current user test target has moved from BlueStacks to LDPlayer.

The completed gesture spec is:

```text
docs/specs/0014-mobile-gestures.md
```

The next slice should focus on:

1. Real LDPlayer guided calibration for scroll distances and screen dimensions.
2. User-test the exact `calibration guide` command shown by `record-ui`, especially Windows path quoting.
3. User-test the post-action Template nudge after taps and gestures, especially whether cropped templates are stable enough.
4. User-test the new gesture + capture loop, especially whether waits and screenshot transitions feel predictable enough for daily recording.
5. A first bounded decision loop that chooses the next safe scripted step from screenshots and template matches, then stops for review before real device input.

The draft spec for this slice is:

```text
docs/specs/0020-guided-gesture-calibration.md
```

### Why this is next

The current recorder can now tap, wait, and author gestures. Real daily tasks still need stronger post-action verification:

- gestures need calibrated distances per emulator profile
- scroll/swipe flows should create checkpoints after movement
- scripts should fail early when a gesture lands on an unexpected screen
- future AI calls need bounded choose-next-step behavior, not unrestricted clicking
- local AI integration should use a callable tool boundary such as MCP or a local JSON bridge; skills remain the instruction layer, not the execution layer

Without calibration and checkpoints, gestures are available but still too coordinate-heavy for robust daily automation.

## Recommended next implementation order

1. Run `py -m autoplay calibration guide --serial ... --from-screenshot ...` on a real LDPlayer screen and inspect the saved JSON/notes.
2. Confirm the `record-ui` hint works in Windows PowerShell for normal and space-containing paths.
3. Use a real LDPlayer pass to tune vertical/horizontal defaults, then record the result as local artifacts.
4. Feed those findings back into checkpoint-after-gesture guidance before starting the bounded decision loop.
5. Draft the local AI bridge contract, then expose it through MCP when the target local AI client supports MCP.
6. Keep adding unit coverage around any new UI/server payload shape before branching recorder state further.

### Initial gesture semantics

Implemented conservative defaults:

- `swipe`: explicit `x1`, `y1`, `x2`, `y2`, `duration_ms`, optional `label`
- `drag`: same command shape as swipe, but preserve the step type and label for readability
- `scroll`: `direction`, optional `distance`, optional `duration_ms`; compile to a screen-relative swipe
- `back`: Android back key event

Suggested validation bounds:

- coordinates must be non-negative integers
- duration must be between `50` and `5000` ms
- scroll direction must be one of `up`, `down`, `left`, `right`
- real execution remains opt-in

### Recorder UI state

The Web UI stays simple:

- Tap still comes from clicking the screenshot.
- Swipe, drag, and scroll can be authored directly on the screenshot canvas through a tool selector.
- Scroll is still available as four direction buttons plus distance/duration fields when users want a quick fallback.
- Back is a single button that appends a `back` step.
- In device mode, tap and gestures can execute one step at a time, wait, and capture the next screen.
- Gestures work with the existing dry-run test and real-test buttons.

## Existing recorder improvement backlog

Continue improving the guided recorder command when it helps the mobile gesture work:

```powershell
py -m autoplay record scripts\my-daily.yml
```

The recorder currently:

1. Start from a YAML output path.
2. Offer commands such as `screenshot`, `tap X Y LABEL`, `swipe`, `drag`, `scroll`, `back`, `wait SECONDS`, `checkpoint_exists PATH`, `checkpoint_match SOURCE TEMPLATE`, `done`.
3. Append steps to the YAML file after each accepted command.
4. Validate after each append.
5. Never send real taps or gestures during guided recording.

Future improvements should:

1. Optionally write a report or draft notes under `artifacts/`.
2. Improve prompts and recovery for validation errors.
3. Keep refining direct canvas gesture authoring if user testing still finds the recorder too coordination-heavy.

## Core API direction

Create an internal API layer separate from CLI parsing. Suggested module:

```text
src/autoplay/api.py
```

Suggested functions:

- `doctor(adb_path=None, serial=None) -> DoctorReport`
- `screenshot(out, adb_path=None, serial=None) -> AdbResult`
- `tap(x, y, adb_path=None, serial=None, execute=False) -> AdbResult`
- `swipe(x1, y1, x2, y2, duration_ms=300, adb_path=None, serial=None, execute=False) -> AdbResult`
- `drag(x1, y1, x2, y2, duration_ms=700, adb_path=None, serial=None, execute=False) -> AdbResult`
- `scroll(direction, distance=None, duration_ms=400, adb_path=None, serial=None, execute=False) -> AdbResult`
- `back(adb_path=None, serial=None, execute=False) -> AdbResult`
- `validate(script_path) -> ValidationReport`
- `run(script_path, execute_taps=False, report_out=None) -> RunnerReport`
- `match(source, template, threshold=0.95, tolerance=0, region=None) -> MatchResult`

AI-facing tools should call this API rather than shelling out to CLI commands.

## Safety rules for AI tool use

- Default all device input to dry-run.
- Require an explicit `execute=True` or equivalent for real taps and gestures.
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

`0013-recorder-ui-refresh.md` is implemented for the Chinese UI refresh and auto wait handling.

`0014-mobile-gestures.md` is implemented for mobile gesture primitives across the stack.

`0015-checkpoint-authoring-foundation.md` is implemented for guided recorder `checkpoint_match` authoring and gesture helper cleanup.

`0016-record-ui-template-cropping.md` is implemented for browser template cropping and automatic `checkpoint_match` insertion.

`0017-record-ui-direct-gesture-authoring.md` is implemented for screenshot-first swipe/drag/scroll authoring, visual gesture overlays, and recorder workflow polish.

`0018-gesture-capture-loop.md` is implemented for one-step gesture execution with wait-and-capture in recorder device mode.

`0019-bluestacks-gesture-calibration-profile.md` is implemented for serial-aware calibration profile loading, CLI profile authoring, calibrated scroll execution, and recorder UI calibration visibility.

`0020-guided-gesture-calibration.md` is implemented as the CLI-first guided calibration slice.

`0021-post-action-checkpoint-nudge.md` is implemented as a recorder UI workflow nudge after device actions.

`0022-local-ai-tool-interface.md` is drafted as the bridge contract for local AI and future MCP wrapping.

Next, test `calibration guide` results, the record-ui guide command, and template stability on real LDPlayer, then build a bounded decision loop that uses screenshots and template matches to choose the next safe YAML/script step.
