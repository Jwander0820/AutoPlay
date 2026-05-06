# 0022 Local AI Tool Interface

## Intent

Define the first AI-callable interface for local assistants. The interface should be usable as a plain JSON bridge first and later be wrapped as MCP without changing the core AutoPlay API.

## Decision

AutoPlay should not rely on a skill alone for execution.

- A skill can tell an AI how to use AutoPlay.
- A JSON bridge or MCP server should expose actual callable tools.
- Tool implementation should call `AgentSession`, not raw ADB or unrestricted CLI commands.

## Proposed Tool Contract

All requests use this shape:

```json
{
  "tool": "screenshot",
  "args": {
    "out": "artifacts/ai/current.png"
  }
}
```

All responses use this shape:

```json
{
  "ok": true,
  "tool": "screenshot",
  "result": {},
  "messages": []
}
```

## Initial Tools

- `doctor`: return emulator readiness.
- `screenshot`: capture to `artifacts/`.
- `match`: run template matching on `artifacts/` images.
- `tap`: dry-run by default; real input requires explicit execution and policy opt-in.
- `swipe`: dry-run by default.
- `drag`: dry-run by default.
- `scroll`: dry-run by default.
- `back`: dry-run by default.
- `validate`: validate a YAML script.
- `draft_script`: write a reviewable YAML draft under `scripts/` without touching ADB.
- `run_script`: validate and run a YAML script, dry-run by default.

## Implemented Surface

The first bridge is `src/autoplay/ai_bridge.py`.

- `AiBridge.handle(request)` accepts the JSON request object directly and returns the JSON response object.
- `AiBridge.from_local_config(...)` reads ignored local defaults for `adb_path` and `serial`, while keeping `allow_device_input` opt-in at the bridge/session level.
- `python -m autoplay ai-tool request.json` runs one request through the bridge.
- `python -m autoplay ai-tool -` reads a request from stdin.
- `python -m autoplay ai-schemas` prints machine-readable tool schemas for local AI clients.
- `python -m autoplay ai-examples` prints machine-readable example requests for local AI clients.
- `--out` writes the response JSON to a file; otherwise it prints to stdout.
- `--artifact-root`, `--audit-out`, `--step-budget`, `--adb-path`, and `--serial` allow test wrappers and future MCP servers to avoid private committed defaults.
- `python -m autoplay ai-server` starts a local HTTP JSON server on `127.0.0.1:8787`.
- `ai-server --allow-device-input` generates a session-only device input code unless `--device-input-code` is provided.
- `GET /health` returns service readiness, supported tools, and remaining step budget.
- `GET /tools` returns the supported tool names.
- `GET /schemas` and `GET /schema` return full tool descriptions, safety levels, args schemas, and request schemas.
- `GET /examples` and `GET /example-requests` return canonical safe example requests.
- `POST /tool` and `POST /api/tool` accept the same JSON request object as `ai-tool`.

Example dry-run tap request:

```json
{
  "tool": "tap",
  "args": {
    "x": 100,
    "y": 200,
    "label": "open daily panel"
  }
}
```

Example real tap request, still requiring `ai-tool --allow-device-input` or equivalent bridge config:

```json
{
  "tool": "tap",
  "args": {
    "x": 100,
    "y": 200,
    "label": "open daily panel",
    "execute": true,
    "device_input_code": "CODE-SHOWN-IN-LAUNCHER"
  }
}
```

When a device input code is configured, real input requests must include both `args.execute=true` and `args.device_input_code` with the current value. This keeps persistent local servers usable while making real emulator input visibly consented by the human operator.

Example HTTP call shape:

```http
POST /tool HTTP/1.1
Content-Type: application/json

{
  "tool": "scroll",
  "args": {
    "direction": "down",
    "label": "inspect next task",
    "distance": 700
  }
}
```

The schema payload uses this shape:

```json
{
  "ok": true,
  "schema_version": "2026-05-05",
  "request_shape": {
    "tool": "<tool name>",
    "args": {}
  },
  "tools": [
    {
      "name": "tap",
      "description": "Tap a coordinate. Dry-run unless args.execute=true and server/session policy allows real input.",
      "safety": "device_input_guarded",
      "args_schema": {},
      "request_schema": {}
    }
  ]
}
```

## Safety Requirements

- Default to dry-run for every device input tool.
- Require local policy opt-in before real input.
- Require explicit per-call execution request before real input.
- Require the current `device_input_code` before real input when the bridge/server is configured with one.
- Preserve step budgets.
- Write JSONL audit logs.
- Keep screenshots, templates, reports, and AI artifacts under `artifacts/`.
- Block unsafe intents and labels using the existing AI-facing safety policy.

## MCP Mapping

When adding MCP, each JSON bridge tool maps to one MCP tool with the same argument schema. The MCP layer should stay thin:

```text
MCP request -> JSON bridge -> AgentSession -> api.py -> ADB
```

The HTTP server is not the final MCP server. It is a local compatibility rail for early testing and for AI clients that can call HTTP tools before MCP integration exists.

This keeps local AI clients replaceable and avoids coupling AutoPlay to one chat application.

## Acceptance Criteria

- A local AI client can call `doctor` and `screenshot` without shelling out.
- Dry-run `tap` and `scroll` return the exact ADB command that would run.
- Real input is blocked unless both session policy and tool args allow it.
- Persistent server real input is blocked unless the current device input code is supplied.
- All AI calls are audited.
- User-specific ADB paths are loaded from ignored local config, not committed files.
- A local HTTP client can call `/health`, `/tools`, and `/tool` without adding third-party server dependencies.
- A local AI client can call `/schemas` or `ai-schemas` to discover arguments before invoking `/tool`.
- A local AI client can call `/examples` or `ai-examples` to retrieve concrete request examples without scraping docs.
