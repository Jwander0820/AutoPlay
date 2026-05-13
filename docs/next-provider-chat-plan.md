# Next Provider Chat Phase Plan - 2026-05-14

## Current Checkpoint

AutoPlay now has a safe local AI provider-chat foundation:

- JSON bridge, HTTP bridge, MCP adapter manifest, MCP stdio server, and MCP smoke client.
- Provider chat loop for Ollama, LM Studio, and OpenAI-compatible chat completions.
- `ai-chat-smoke` fake-provider path that tests the production chat/tool loop without an external model.
- Tool allowlists through `--tool`, capped tool calls through `--max-tool-calls`, and sanitized transcripts through `--transcript-out`.
- All model tool calls still route through `AiBridge -> AgentSession -> api.py`.

## Next Phase Goals

### 1. Manual Provider Validation

- Run `ai-chat-smoke` on Windows before every provider test.
- Test Ollama with one local model using `--tool draft_script`.
- Test LM Studio with one loaded model using `--tool draft_script` and `--tool validate`.
- Test OpenAI only with non-sensitive prompts and sanitized transcripts.
- Record provider behavior, model names, tool-call format quirks, and transcript notes in `docs/stage-report.md`.

### 2. Provider UX Hardening

- Add a small provider diagnostics command if manual testing shows setup confusion.
- Improve error messages for connection refused, missing local server, missing OpenAI key, and model-not-loaded cases.
- Keep API keys runtime-only; do not write keys into config, examples, transcripts, or docs.

### 3. Review-First Chat Workflow

Prefer this chain for real use:

```text
user intent -> ai-chat draft_script -> validate -> dry-run run_script -> transcript review -> guarded real input
```

- Keep `draft_script`, `validate`, and dry-run `run_script` as the default allowlisted tools for provider chat.
- Do not enable real device input from provider chat until a human has reviewed the generated YAML and dry-run report.

### 4. Checkpoint-First Automation Planning

- After provider chat is manually validated, add a bounded planner that asks the model to draft checkpoint-first YAML.
- Keep the planner output as reviewable files under `scripts/`.
- Require template/checkpoint evidence before any future decision loop can choose device input.

## Definition Of Done

- Ollama and LM Studio each have one recorded successful dry-run provider test.
- OpenAI compatibility is verified with a non-sensitive draft-only prompt, or explicitly deferred.
- Provider setup errors are clear enough for a user to recover without reading source code.
- Stage report documents exact commands, outputs, safety notes, and remaining risks.
- Full test suite remains green.
