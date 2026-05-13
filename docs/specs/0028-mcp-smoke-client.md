# 0028 - MCP Smoke Client

## Intent

AutoPlay should provide a one-command smoke test for the MCP stdio server so local AI integration can be checked before wiring an external client.

The smoke client is an integration check, not a second execution path.

## Behavior

- `py -m autoplay ai-mcp-smoke` runs the MCP stdio server in memory.
- By default it sends:
  - `initialize`
  - `notifications/initialized`
  - `tools/list`
- The command prints JSON containing:
  - `ok`
  - `protocol_version`
  - `tool_count`
- `--example <name>` can run a canonical example through MCP `tools/call`.
- The example names are the same examples exposed by `ai-examples`.
- Tool call results are included as MCP tool result JSON.

## Safety

- Guarded real-input examples are rejected by default.
- `--allow-real-examples` is required before the smoke client will run an example that asks for `execute=true`.
- Even with `--allow-real-examples`, real input still requires the MCP server config and bridge policy to allow device input.
- Tool calls still route through `AiBridge -> AgentSession -> api.py`.
- Smoke output is machine-readable JSON so local automation can fail fast.

## Acceptance Criteria

- Unit tests prove the smoke client checks initialize and tool listing without running a tool.
- Unit tests prove a dry-run example can run through MCP `tools/call`.
- Unit tests prove guarded real-input examples are rejected by default.
- CLI tests prove `ai-mcp-smoke --out` writes valid JSON.
- The full test suite remains green.
