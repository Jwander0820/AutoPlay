# 0008 Agent Run CLI

## Status

Implemented.

## Summary

AutoPlay exposes a first user-testable AI automation rail through `py -m autoplay agent-run`. The command runs an existing YAML script through `AgentSession`, producing both a runner report and an agent audit log while preserving dry-run defaults.

## Behavior

- `py -m autoplay agent-run <script.yml>` validates a script through the agent session, then runs it through the same session.
- Default outputs:
  - Report: `artifacts/reports/<script-stem>-agent-dry-run.json`
  - Audit: `artifacts/agent/<script-stem>-audit.jsonl`
- Options:
  - `--artifact-root PATH`
  - `--report-out PATH`
  - `--audit-out PATH`
  - `--step-budget N`
  - `--intent TEXT`
  - `--execute-taps`
  - `--allow-device-input`
- The command prints validation output, executed step summaries, dry-run/real-tap status, report path, and audit path.

## Safety

- Tap execution remains dry-run by default.
- Real tap execution requires both `--execute-taps` and `--allow-device-input`.
- Report and audit output paths must satisfy `AgentPolicy` artifact rules.
- Blocked agent actions exit non-zero and are written to the audit log when the safety session reaches the attempted tool call.

## Acceptance

- Agent runner tests cover default report/audit writing, validation failure, and real-tap blocking.
- CLI tests cover `agent-run` report and audit creation.
- User testing docs include dry-run agent testing before any real tap execution.
