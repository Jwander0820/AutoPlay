# 0007 Agent Tool Safety

## Status

Implemented.

## Summary

AutoPlay includes an AI-facing session wrapper around the core API. The wrapper is designed for future agent loops that can inspect screenshots, validate scripts, match templates, and run bounded daily-task scripts while preserving dry-run defaults and auditability.

## Behavior

- `AgentSession` lives in `src/autoplay/agent_tools.py`.
- The session exposes `doctor`, `screenshot`, `tap`, `validate`, `run`, and `match` methods backed by `autoplay.api`.
- Every tool invocation consumes one step from `AgentPolicy.step_budget`.
- Every successful, failed, or blocked invocation writes one JSONL audit event to `AgentPolicy.audit_path`.
- Audit events include timestamp, tool name, status, step budget state, metadata, result summary, and error text when relevant.
- Screenshot outputs, match images, and run reports must live under `AgentPolicy.artifact_root` by default.

## Safety

- Device input remains dry-run by default.
- Real tap execution requires both a method-level execution request and `AgentPolicy.allow_device_input=True`.
- Attempts to execute real taps without policy opt-in are blocked and audited.
- Agent runs inspect tap labels and reject blocked intents such as purchases, gacha, trading, deletion, chat, PvP, verification-code handling, credential entry, anti-cheat bypass, root/hook, and memory modification.
- Step-budget exhaustion blocks further tool calls before touching the core API.

## Acceptance

- Tests cover dry-run tap defaults, real-tap blocking, explicit policy opt-in, step-budget exhaustion, artifact path enforcement, unsafe script label blocking, dry-run script execution, and audit log writing.
