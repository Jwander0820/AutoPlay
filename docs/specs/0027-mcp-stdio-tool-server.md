# 0027 - MCP Stdio Tool Server

## Intent

AutoPlay should expose its existing AI bridge tools through a minimal MCP stdio transport so local AI clients can connect without custom HTTP glue.

The MCP layer is transport glue only. It must not duplicate safety policy or execute project APIs directly.

## Behavior

- `py -m autoplay ai-mcp-stdio` starts a newline-delimited JSON-RPC server on stdin/stdout.
- The server supports:
  - `initialize`
  - `notifications/initialized`
  - `ping`
  - `tools/list`
  - `tools/call`
- `initialize` returns the latest supported protocol version when the client requests an unsupported one.
- `tools/list` returns MCP-shaped tools derived from the adapter manifest.
- `tools/call` accepts `params.name` and optional `params.arguments`, then routes to `AiBridge`.
- Tool call results include both text content and structured JSON content.
- Tool-level failures from `AiBridge` are returned as MCP tool results with `isError: true`, so a client can inspect and recover.
- Unknown MCP methods return JSON-RPC errors.

## Safety

- The stdio server writes only valid JSON-RPC messages to stdout.
- Diagnostic text must not be printed to stdout while the stdio server is running.
- Device input remains dry-run unless session policy, call arguments, and optional `device_input_code` allow it.
- All tool calls go through `AiBridge -> AgentSession -> api.py`.
- Audit logs, step budgets, artifact path checks, and blocked intent checks remain owned by `AgentSession`.

## Acceptance Criteria

- Unit tests cover `initialize`, `tools/list`, `tools/call`, notifications, and unknown methods.
- Unit tests prove newline-delimited stdio reads and writes valid JSON-RPC messages.
- CLI tests prove `ai-mcp-stdio` passes runtime options into the stdio server.
- Existing AI bridge, HTTP server, CLI, and full test suite continue to pass.
