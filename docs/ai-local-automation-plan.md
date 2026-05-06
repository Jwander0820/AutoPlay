# Local AI Automation Plan

## Goal

AutoPlay should eventually let the user talk to a local AI assistant and ask it to perform bounded emulator tasks, while keeping every real device action reviewable, auditable, and easy to stop.

Example future flow:

```text
User chat -> local AI -> AutoPlay tool interface -> safety session -> ADB/API -> emulator
```

## MCP Or Skill

Use both, but for different jobs.

- Skill: good for teaching an AI how this repository works, what safety rules matter, and how to produce scripts or plans.
- MCP or a local tool server: needed when the AI must actually call tools, inspect screenshots, run template matches, or send dry-run/real actions.

The recommended path is:

1. Keep `src/autoplay/api.py` as the stable Python core.
2. Keep `src/autoplay/agent_tools.py` as the safety wrapper for AI-facing calls.
3. Use `src/autoplay/ai_bridge.py` as the local JSON bridge over the same safety wrapper.
4. Wrap that bridge as MCP when the target local AI client supports MCP.
5. Keep the skill as the instruction layer for AI agents that can read repository context.

## User Experience Direction

The human-facing path should stay convenient:

- `run_autoplay.cmd` opens the Traditional Chinese launcher.
- The launcher manages emulator profile, ADB path, serial, connect targets, screenshots, smoke tests, and Recorder UI.
- User-specific paths live in `config/autoplay.local.json`, which is ignored by git.
- Recorder UI should keep showing the current execution context: ADB, serial, device-input mode, and the record/test/checkpoint workflow.

## AI Tool Boundary

AI-callable tools should be intentionally small:

- `doctor`: inspect emulator readiness.
- `screenshot`: capture to an artifact path.
- `match`: compare screenshot/template regions.
- `tap`, `swipe`, `drag`, `scroll`, `back`: dry-run by default.
- `draft_script`: write reviewable YAML under `scripts/` without touching the device.
- `run_script`: validate and run a YAML script, dry-run by default.
- `save_plan` or `draft_script`: write reviewable YAML without touching the device.

The first testable execution entrypoint is:

```text
python -m autoplay ai-tool request.json --artifact-root artifacts
```

For local AI clients that prefer a persistent process, use:

```text
python -m autoplay ai-server --host 127.0.0.1 --port 8787
```

For tool discovery, the same contract is available from:

```text
python -m autoplay ai-schemas
GET http://127.0.0.1:8787/schemas
```

For concrete request examples, use:

```text
python -m autoplay ai-examples
GET http://127.0.0.1:8787/examples
```

For end-to-end local server smoke testing, use:

```text
python -m autoplay ai-smoke --base-url http://127.0.0.1:8787
python -m autoplay ai-smoke --example dry_run_tap
```

This is intentionally wrapper-friendly: a PyCharm Run Configuration, a local chat client, a simple HTTP caller, or a future MCP server can all produce the same JSON request and consume the same JSON response.

Real device input must require all of these:

- local config or session policy allows device input
- explicit tool argument requests execution
- current device input code is supplied when one is configured
- audit log is written
- step budget remains
- blocked unsafe intent checks pass

## Compatibility Direction

Emulator differences should be isolated behind profiles:

- ADB executable candidates
- connect targets and ports
- window title hints for live-click recording
- calibration profiles keyed by serial and screen dimensions

The core API should continue using standard ADB commands so BlueStacks, LDPlayer, Android Emulator, and physical devices stay compatible where their ADB behavior matches.

## Roadmap

1. Human testing quality: improve launcher and Recorder UI until emulator smoke testing is a one-button workflow.
2. Recorder reliability: make checkpoint authoring and template preview easier after every device action.
3. AI bridge: define a local JSON tool boundary that calls `AgentSession`.
4. MCP server: expose the AI bridge to local AI clients that support MCP.
5. Local chat workflow: let the AI propose a plan, generate/update YAML, dry-run it, then ask before any real device input.
6. Decision loop: use screenshots and template matches to choose the next safe scripted step, then stop for review before execution.
