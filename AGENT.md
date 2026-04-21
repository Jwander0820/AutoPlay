# AutoPlay Agent Guide

## Project intent

AutoPlay is a local automation project for BlueStacks and similar Android emulator workflows. Treat this repository as the source of truth for implementation details, product decisions, safety rules, and local automation behavior.

The long-term goal is to let an AI assistant help complete repetitive daily tasks, eventually including safe game-assistance workflows. Progress toward that goal must stay incremental, auditable, and bounded by explicit safety controls.

## Working rules

- Read the existing files before making changes.
- Keep changes small, focused, and consistent with the current structure.
- Prefer clear names and simple modules over early abstractions.
- Do not overwrite user-created files or generated assets without checking their purpose.
- When adding behavior, include a practical way to verify it.
- Use SDD: update the relevant spec before or alongside behavior changes, then add tests that prove the spec.

## Skill entrypoint

Use the project skill at `skills/autoplay/SKILL.md` when work involves AutoPlay-specific planning, architecture, automation behavior, or project conventions.

## Engineering documents

- SDD workflow: `docs/sdd.md`
- Current architecture: `docs/architecture.md`
- Maintenance loop: `docs/maintenance.md`
- User testing guide: `docs/user-testing.md`
- Personal script workflow: `docs/personal-scripts.md`
- Next-stage handoff: `docs/next-stage.md`
- Implemented specs: `docs/specs/`

## Autonomous maintenance loop

- Treat every user test failure as input for the next spec.
- Prefer adding diagnostics before adding more automation surface.
- Keep the project runnable without BlueStacks for unit tests.
- Preserve safety defaults: validation first, dry-run taps by default, explicit flags for device input.

## Current automation foundation

- BlueStacks ADB control is available through `AdbClient`.
- CLI commands exist for `doctor`, `screenshot`, `tap`, `run`, `validate`, `match`, `record`, `agent-run`, `click-map`, `record-ui`, and `record-clicks`.
- YAML DSL supports screenshots, waits, taps, checkpoint existence checks, and template match checkpoints.
- Core CLI behavior is API-ized in `src/autoplay/api.py` so recorders, AI tools, and future decision loops can call Python functions instead of shelling out.
- Guided script creation is available through `src/autoplay/recorder.py` and `py -m autoplay record <script.yml>`.
- Screenshot-based coordinate collection is available through `py -m autoplay click-map <screenshot.png> --out <page.html>`.
- Browser-based script recording is available through `py -m autoplay record-ui <script.yml> --screenshot <screen.png>`.
- The recorder UI is a Traditional Chinese workspace with repeated capture, script-only/device modes, manual/auto wait modes, dry-run/real script test buttons, profile serial preservation, and an explicit opt-in tap/capture flow for multi-screen scripts.
- Experimental Windows live-click recording is available through `py -m autoplay record-clicks <script.yml>` for BlueStacks windows.
- AI-facing automation tools are wrapped by `src/autoplay/agent_tools.py`, which enforces dry-run defaults, step budgets, audit logs, artifact-root checks, and blocked unsafe intents.
- `py -m autoplay agent-run <script.yml>` is the first user-testable AI automation rail for running validated scripts through the safety wrapper.

## Implemented specs

- `docs/specs/0005-guided-recorder.md`: interactive YAML script authoring.
- `docs/specs/0006-core-api.md`: stable Python API for CLI and AI tool calls.
- `docs/specs/0007-agent-tool-safety.md`: bounded AI tool invocation rules and audit logs.
- `docs/specs/0008-agent-run-cli.md`: user-testable agent-run command.
- `docs/specs/0009-click-map-helper.md`: screenshot coordinate mapping helper.
- `docs/specs/0010-record-ui.md`: browser-based recorder UI with direct YAML save and validation.
- `docs/specs/0011-live-click-recorder.md`: experimental Windows live-click capture for BlueStacks.
- `docs/specs/0012-continuous-recorder-ui.md`: repeated capture and tap/wait/capture flows.
- `docs/specs/0013-recorder-ui-refresh.md`: Chinese UI refresh and auto wait handling.

## Next stage direction

- Use real BlueStacks user testing to calibrate screenshot dimensions, click coordinates, and window/client-area mapping.
- Improve script authoring from "record taps" into "record intent": add template-cropping, checkpoint creation, and screen-change detection after actions.
- Build a first bounded decision loop that can inspect a screenshot, run template matches, choose the next safe scripted step, and stop for review before any real tap execution.
- Keep AI-facing APIs behind the same safety model: dry-run by default, explicit execution flags, validation before device input, step budgets, audit logs, and JSON reports for every run.
- Do not give AI an unrestricted loop that freely clicks the device. Prefer bounded tool calls, reviewable plans/scripts, and explicit user opt-in for real device input.

## Git workflow

- Keep generated caches, dependency folders, logs, and local environment files out of git.
- Make commits only when asked.
- Before committing, follow the local `commit-security-audit` skill: inspect staged scope, scan for secrets/credentials/database details, exclude personal scripts and artifacts, run relevant tests, then commit.
- Commit messages must follow the local `commit-message-style` skill: `<type>: <Traditional Chinese subject>`, one Traditional Chinese summary paragraph, then numbered Traditional Chinese change details.
- Before handing work back, run the smallest relevant verification command and report anything that could not be checked.
