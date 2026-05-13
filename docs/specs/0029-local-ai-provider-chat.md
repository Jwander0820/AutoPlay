# 0029 - Local AI Provider Chat

## Intent

AutoPlay should let the user connect a local or hosted chat model to the existing AI tool bridge. The first supported providers are Ollama, LM Studio, and OpenAI.

This feature is a provider adapter and tool loop. It must not create a new automation safety path.

## Provider APIs

- Ollama uses `POST /api/chat`.
- LM Studio uses its OpenAI-compatible `POST /v1/chat/completions` endpoint.
- OpenAI uses `POST /v1/chat/completions`.
- The implementation uses standard library HTTP only; no provider SDK is required.

## Behavior

- `py -m autoplay ai-chat` accepts:
  - `--provider ollama|lmstudio|openai`
  - `--model`
  - `--prompt`
  - optional `--base-url`
  - optional `--api-key`
  - optional repeated `--tool` allowlist entries
  - optional `--transcript-out`
  - optional bridge safety/session flags
- The command sends AutoPlay tool schemas as chat function tools.
- When `--tool` is supplied, only those tools are exposed to the provider.
- A provider tool call outside the allowlist fails before reaching `AiBridge`.
- If the model returns tool calls, AutoPlay maps them to existing AI bridge requests.
- Tool calls are capped by `--max-tool-calls`.
- Provider `--base-url` may be either a service root or the full chat endpoint.
- `lm-studio` and `lmstudio` are accepted as the same provider.
- Tool calls named `autoplay.<tool>` are normalized back to the bridge tool name.
- Malformed tool argument JSON raises a clear `AiChatError`.
- If the model requests more tool calls than allowed, the result is marked `incomplete` and `ok: false`.
- A sanitized transcript records request turns, assistant messages, and redacted tool results.
- `py -m autoplay ai-chat-smoke` uses the same chat/tool-loop code path with an in-memory fake provider.
- The smoke command drafts a wait-only YAML script under the artifact root and writes the same machine-readable result shape.
- The command prints machine-readable JSON with:
  - `ok`
  - `provider`
  - `model`
  - `final_message`
  - `tool_calls`
  - `tool_results`
  - `incomplete`
  - `transcript`

## Safety

- Every tool call routes through `AiBridge -> AgentSession -> api.py`.
- The chat provider never receives raw ADB access.
- Tool results sent back to the model redact local command paths.
- Sanitized transcripts also redact local command paths and absolute local file paths.
- Real device input remains blocked unless the bridge/session allows device input and the tool call explicitly asks for `execute=true`.
- `device_input_code` is still required when configured.
- The system prompt instructs models to prefer `draft_script -> validate -> dry-run run_script -> human review`.
- API keys must be supplied through `--api-key` or environment variables and must not be written into docs, examples, or committed config.

## Acceptance Criteria

- Unit tests prove OpenAI-compatible providers call `/v1/chat/completions`.
- Unit tests prove Ollama calls `/api/chat`.
- Unit tests prove full endpoint URLs are not double-appended.
- Unit tests prove model tool calls execute through `AiBridge`.
- Unit tests prove prefixed tool call names and malformed arguments are handled.
- Unit tests prove tool-call limit exhaustion marks the result incomplete.
- Unit tests prove allowlisted tools are the only visible and callable tools.
- CLI tests prove `--transcript-out` writes a sanitized transcript.
- CLI tests prove `ai-chat-smoke` can exercise the provider chat loop without an external model.
- Unit tests prove OpenAI requires an API key.
- CLI tests prove `ai-chat --out` writes machine-readable JSON.
- Existing AI bridge, MCP, HTTP server, and full test suite remain green.
