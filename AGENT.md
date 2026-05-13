# AutoPlay Agent Guide

## Project intent

AutoPlay is a local automation project for Android emulator workflows. BlueStacks and LDPlayer are the first supported Windows profiles. Treat this repository as the source of truth for implementation details, product decisions, safety rules, and local automation behavior.

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
- Next phase plan: `docs/next-phase-plan.md`
- Provider chat next phase plan: `docs/next-provider-chat-plan.md`
- Local AI automation plan: `docs/ai-local-automation-plan.md`
- Latest stage report: `docs/stage-report.md`
- Implemented specs: `docs/specs/`

## Autonomous maintenance loop

- Treat every user test failure as input for the next spec.
- Prefer adding diagnostics before adding more automation surface.
- Keep the project runnable without a real emulator for unit tests.
- Preserve safety defaults: validation first, dry-run device input by default, explicit flags for taps and gestures.

## Current automation foundation

- Android emulator ADB control is available through `AdbClient`.
- CLI commands exist for `doctor`, `screenshot`, `tap`, `swipe`, `drag`, `scroll`, `back`, `calibration`, `run`, `validate`, `match`, `record`, `agent-run`, `click-map`, `record-ui`, and `record-clicks`.
- YAML DSL supports screenshots, waits, taps, mobile gestures, checkpoint existence checks, and template match checkpoints.
- Core CLI behavior is API-ized in `src/autoplay/api.py` so recorders, AI tools, and future decision loops can call Python functions instead of shelling out.
- Guided script creation is available through `src/autoplay/recorder.py` and `py -m autoplay record <script.yml>`.
- Screenshot-based coordinate collection is available through `py -m autoplay click-map <screenshot.png> --out <page.html>`.
- Browser-based script recording is available through `py -m autoplay record-ui <script.yml> --screenshot <screen.png>`.
- PyCharm/CMD-friendly launcher entrypoints are available through `run_autoplay.py` and `run_autoplay.cmd`.
- The launcher supports emulator profiles, local default saving, ADB/serial/connect-target configuration, one-click smoke testing, screenshots, dry-run device actions, confirmed real actions, and Recorder UI startup.
- User-specific launcher settings live in ignored `config/autoplay.local.json`; the tracked template is `config/autoplay.example.json`.
- The recorder UI is a Traditional Chinese workspace with repeated capture, script-only/device modes, manual/auto wait modes, direct-manipulation gesture tools on the screenshot canvas, dry-run/real script test buttons, profile serial preservation, and an explicit opt-in tap/capture flow for multi-screen scripts.
- The recorder UI now surfaces connection/capture/record/validation workflow state plus device input, serial, and ADB context.
- Experimental Windows live-click recording is available through `py -m autoplay record-clicks <script.yml>` for matching emulator windows.
- AI-facing automation tools are wrapped by `src/autoplay/agent_tools.py`, which enforces dry-run defaults, step budgets, audit logs, artifact-root checks, and blocked unsafe intents.
- `py -m autoplay agent-run <script.yml>` is the first user-testable AI automation rail for running validated scripts through the safety wrapper.
- `src/autoplay/ai_bridge.py` and `py -m autoplay ai-tool <request.json>` provide the first JSON bridge for local AI clients and future MCP wrapping.
- `py -m autoplay ai-server` exposes the same JSON bridge over local HTTP (`/health`, `/tools`, `/tool`) for early local AI integration before MCP.
- `src/autoplay/ai_schemas.py`, `py -m autoplay ai-schemas`, and `GET /schemas` expose machine-readable tool schemas so local AI clients can discover arguments before invoking tools.
- `src/autoplay/ai_examples.py`, `py -m autoplay ai-examples`, and `GET /examples` expose safe canonical request examples for local AI integration.
- `src/autoplay/ai_client.py` and `py -m autoplay ai-smoke` provide an end-to-end local AI server smoke test for health, schemas, examples, and optional safe example execution.
- `draft_script` lets AI clients write reviewable YAML drafts under `scripts/` through `AgentSession`, with validation and audit logs, while rejecting private `profile.adb_path`.
- Real device input through AI bridge/server can require a session-only `device_input_code`; `ai-server --allow-device-input` generates and prints one when omitted.
- `src/autoplay/ai_adapter.py`, `py -m autoplay ai-adapter`, `GET /adapter`, `GET /mcp/tools`, and `POST /mcp/call` provide a thin MCP/local-client adapter manifest and call shape while still routing every call through `AiBridge`.
- `src/autoplay/ai_mcp.py` and `py -m autoplay ai-mcp-stdio` expose a minimal newline-delimited MCP stdio server for `initialize`, `tools/list`, and `tools/call` over the same bridge.
- `src/autoplay/ai_mcp_client.py` and `py -m autoplay ai-mcp-smoke` provide an in-memory MCP smoke test for initialize/tool discovery and optional safe example execution.
- `src/autoplay/ai_chat.py`, `py -m autoplay ai-chat`, and `py -m autoplay ai-chat-smoke` connect Ollama, LM Studio, or OpenAI chat models to AutoPlay tool schemas and route model tool calls through `AiBridge`, with a fake-provider smoke path, endpoint normalization, prefixed tool-name handling, tool allowlists, sanitized transcripts, malformed-argument errors, and local command redaction before model follow-up turns.

## Current stage checkpoint

- This stage completed the first local AI automation toolchain: JSON bridge, local HTTP server, machine-readable schemas, canonical examples, smoke client, guarded real-input consent code, and AI draft-script writing.
- Local AI clients can now discover tools with `ai-schemas`, `ai-adapter`, `GET /schemas`, `GET /adapter`, `GET /mcp/tools`, or MCP `tools/list`; inspect examples with `ai-examples` or `GET /examples`; smoke-test HTTP with `ai-smoke`; smoke-test MCP stdio with `ai-mcp-smoke`; call tools with `ai-tool`, `POST /tool`, `POST /mcp/call`, MCP `tools/call`, or provider-backed `ai-chat`; and write reviewable drafts with `draft_script`.
- Real device input remains guarded by dry-run defaults, session policy, explicit `execute=true`, optional session-only `device_input_code`, step budget, audit logs, and blocked intent terms.
- `draft_script` writes only under `scripts/`, validates immediately, refuses private `profile.adb_path`, and is intended as the preferred AI path before any dry-run or real emulator action.
- This stage completed the gesture-authoring foundation: mobile gestures are supported across the DSL, validation, runner, CLI, API, agent tools, guided recorder, `click-map`, and `record-ui`.
- `record-ui` can now author tap, swipe, drag, scroll, back, wait, screenshot, and `checkpoint_match` steps from the screenshot workspace.
- Device-mode recorder flows can execute one tap or supported gesture, wait manually or until screen stability, capture the next screenshot, and append the reviewable YAML sequence.
- Serial-aware calibration profiles exist through `calibration write/show`, `scroll --calibrated`, recorder profile loading, and visible calibration status in the Web UI.
- `docs/specs/0020-guided-gesture-calibration.md` is implemented as a CLI-first `calibration guide` workflow with dry-run previews, explicit real-scroll confirmation, profile saving, local notes, and tests.
- `record-ui` shows a matching `calibration guide` command when launched with a serial, so tester handoff from screenshot recording to gesture calibration is visible in the UI.
- The launcher and local config foundation now make LDPlayer testing possible without repeatedly typing CLI commands.
- Emulator profile support isolates LDPlayer, BlueStacks, and generic ADB differences without changing the core API.
- `docs/stage-report.md` records the latest emulator compatibility and guided calibration reports, verification commands, and safety notes.
- The next automation boundary is calibration and checkpoint reliability, not unrestricted screen-solving.

## Implemented specs

- `docs/specs/0005-guided-recorder.md`: interactive YAML script authoring.
- `docs/specs/0006-core-api.md`: stable Python API for CLI and AI tool calls.
- `docs/specs/0007-agent-tool-safety.md`: bounded AI tool invocation rules and audit logs.
- `docs/specs/0008-agent-run-cli.md`: user-testable agent-run command.
- `docs/specs/0009-click-map-helper.md`: screenshot coordinate mapping helper.
- `docs/specs/0010-record-ui.md`: browser-based recorder UI with direct YAML save and validation.
- `docs/specs/0011-live-click-recorder.md`: experimental Windows live-click capture for emulator windows.
- `docs/specs/0012-continuous-recorder-ui.md`: repeated capture and tap/wait/capture flows.
- `docs/specs/0013-recorder-ui-refresh.md`: Chinese UI refresh and auto wait handling.
- `docs/specs/0014-mobile-gestures.md`: mobile gesture primitives across ADB, API, YAML, runner, CLI, agent tools, and recorder UI.
- `docs/specs/0015-checkpoint-authoring-foundation.md`: guided recorder checkpoint_match authoring and gesture helper cleanup.
- `docs/specs/0016-record-ui-template-cropping.md`: browser template cropping and checkpoint_match insertion.
- `docs/specs/0017-record-ui-direct-gesture-authoring.md`: direct screenshot gesture authoring and recorder UI workflow polish.
- `docs/specs/0018-gesture-capture-loop.md`: execute-and-capture recorder flow for gestures in device mode.
- `docs/specs/0019-bluestacks-gesture-calibration-profile.md`: serial-aware gesture calibration profile loading, CLI profile authoring, and recorder UI calibration visibility.
- `docs/specs/0020-guided-gesture-calibration.md`: CLI-first workflow for deriving profile values from real emulator tester feedback.
- `docs/specs/0021-post-action-checkpoint-nudge.md`: record-ui nudge that switches to Template mode after device tap/gesture capture, plus checkpoint preview and template quality hints.
- `docs/specs/0022-local-ai-tool-interface.md`: local AI JSON bridge and future MCP tool boundary.
- `docs/specs/0023-local-ai-client-examples.md`: machine-readable local AI example requests.
- `docs/specs/0024-local-ai-smoke-client.md`: local AI server smoke client for health/schema/example/tool verification.
- `docs/specs/0025-ai-draft-script-tool.md`: AI-facing tool for writing reviewable YAML drafts under `scripts/`.
- `docs/specs/0026-local-ai-adapter-manifest.md`: MCP/local-client adapter manifest and adapter call shape over the AI bridge.
- `docs/specs/0027-mcp-stdio-tool-server.md`: minimal MCP stdio transport over the AI bridge.
- `docs/specs/0028-mcp-smoke-client.md`: in-memory MCP smoke client for tool discovery and safe example calls.
- `docs/specs/0029-local-ai-provider-chat.md`: Ollama, LM Studio, and OpenAI chat provider adapter over the AI bridge.

## Next stage direction

- Calibrate mobile gestures on real LDPlayer profiles, especially scroll distance and screen coordinate assumptions.
- Use real LDPlayer testing to validate `calibration guide` output and feed the notes back into profile defaults or UI guidance.
- Keep `calibration guide` bounded: dry-run preview by default, at most one confirmed real scroll per prompt, profile JSON saved only after final confirmation, and local notes written under `artifacts/calibration/`.
- Verify the `record-ui` calibration-guide command on Windows PowerShell with real paths, especially when screenshot paths contain spaces.
- Add checkpoint-first user testing around taps and gestures so flows verify screen state after movement.
- Guided recorder and record-ui can already author `checkpoint_match`; record-ui now nudges testers toward Template mode after device actions. The next work is validating checkpoint quality and decision-loop planning.
- Gesture execute-and-capture is available in device mode; the next work is calibrating it on real LDPlayer screens and tightening post-gesture verification.
- Prefer small typed helpers around recorder payload normalization before adding more recorder endpoints or UI state branches.
- Use real LDPlayer user testing to calibrate screenshot dimensions, click coordinates, and window/client-area mapping.
- Improve script authoring from "record taps" into "record intent": add template-cropping, checkpoint creation, and screen-change detection after actions.
- Build a first bounded decision loop that can inspect a screenshot, run template matches, choose the next safe scripted step, and stop for review before any real tap or gesture execution.
- For local AI conversation, prefer MCP or a local tool server for execution and keep skills as the instruction layer. All tool calls should still pass through `AgentSession` or an equivalent safety wrapper.
- The local JSON AI bridge, thin HTTP server, machine-readable tool schemas, canonical examples, HTTP/MCP smoke clients, AI draft-script tool, adapter manifest, adapter HTTP call endpoint, stdio MCP server, provider-backed `ai-chat`, fake-provider `ai-chat-smoke`, and real-device input code gate now exist; the next phase should manually validate Ollama and LM Studio, then harden provider setup diagnostics.
- Before adding autonomous decision loops, prefer a local chat integration spike that follows this chain: user intent -> `draft_script` -> validate -> dry-run -> human review -> guarded real input.
- The MCP wrapper should stay thin: MCP tool call -> JSON bridge request -> `AgentSession` -> `api.py`; do not duplicate safety policy in the MCP layer.
- Keep AI-facing APIs behind the same safety model: dry-run by default, explicit execution flags, validation before device input, step budgets, audit logs, and JSON reports for every run.
- Do not give AI an unrestricted loop that freely clicks the device. Prefer bounded tool calls, reviewable plans/scripts, and explicit user opt-in for real device input.

## Git workflow

- Keep generated caches, dependency folders, logs, and local environment files out of git.
- Make commits only when asked.
- Before committing, follow the local `commit-security-audit` skill: inspect staged scope, scan for secrets/credentials/database details, exclude personal scripts and artifacts, run relevant tests, then commit.
- Commit messages must follow the local `commit-message-style` skill: `<type>: <Traditional Chinese subject>`, one Traditional Chinese summary paragraph, then numbered Traditional Chinese change details.
- Before handing work back, run the smallest relevant verification command and report anything that could not be checked.
