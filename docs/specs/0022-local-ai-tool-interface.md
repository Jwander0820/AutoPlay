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
- `run_script`: validate and run a YAML script, dry-run by default.

## Safety Requirements

- Default to dry-run for every device input tool.
- Require local policy opt-in before real input.
- Require explicit per-call execution request before real input.
- Preserve step budgets.
- Write JSONL audit logs.
- Keep screenshots, templates, reports, and AI artifacts under `artifacts/`.
- Block unsafe intents and labels using the existing AI-facing safety policy.

## MCP Mapping

When adding MCP, each JSON bridge tool maps to one MCP tool with the same argument schema. The MCP layer should stay thin:

```text
MCP request -> JSON bridge -> AgentSession -> api.py -> ADB
```

This keeps local AI clients replaceable and avoids coupling AutoPlay to one chat application.

## Acceptance Criteria

- A local AI client can call `doctor` and `screenshot` without shelling out.
- Dry-run `tap` and `scroll` return the exact ADB command that would run.
- Real input is blocked unless both session policy and tool args allow it.
- All AI calls are audited.
- User-specific ADB paths are loaded from ignored local config, not committed files.
