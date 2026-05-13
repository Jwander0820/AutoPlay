# 0026 - Local AI Adapter Manifest

## Intent

Local AI clients should be able to discover AutoPlay tools in a shape that is easy to wrap as MCP or a chat-client tool list, without bypassing the existing JSON bridge safety chain.

This is a thin adapter layer. It does not duplicate tool behavior, safety policy, ADB access, validation, or audit logging.

## Behavior

- `py -m autoplay ai-adapter` prints a machine-readable adapter manifest.
- `GET /adapter` and `GET /mcp/tools` return the same manifest from `ai-server`.
- The manifest is derived from `ai_schemas`, so tool names, descriptions, safety tags, and JSON input schemas stay synchronized.
- Each manifest tool includes:
  - `name`
  - `description`
  - `inputSchema`
  - `safety`
  - MCP-style `annotations`
  - the underlying bridge request shape
- `--prefix-names` can prefix tool names with `autoplay.` for clients that share a namespace across many tools.
- Adapter calls use `{ "name": "<tool>", "arguments": {} }` and map to the existing `{ "tool": "<tool>", "args": {} }` bridge request.
- `POST /mcp/call` accepts adapter calls and routes them through `AiBridge`.

## Safety

- Adapter calls must still pass through `AiBridge -> AgentSession -> api.py`.
- Real device input remains dry-run by default.
- Real input still requires server/session policy opt-in, per-call `execute=true`, and `device_input_code` when configured.
- The adapter must not expose raw ADB commands or direct file writes outside the existing bridge tools.
- Unknown adapter tool names return a structured error instead of falling through to arbitrary behavior.

## Acceptance Criteria

- Unit tests prove the adapter manifest mirrors the schema tool list.
- Unit tests prove prefixed tool names map back to bridge requests.
- HTTP tests prove `/adapter` exposes the manifest and `/mcp/call` routes through the bridge.
- CLI tests prove `ai-adapter --out` writes valid JSON.
