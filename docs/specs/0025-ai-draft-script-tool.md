# 0025 AI Draft Script Tool

## Intent

Let local AI clients create reviewable AutoPlay YAML script drafts without touching the emulator. This moves automation from direct action toward auditable script generation.

## Problem

The local AI bridge can validate and run scripts, but it cannot yet create a script draft through the same safety surface. Without a first-party draft tool, local AI clients may write files through ad hoc filesystem access, bypassing path rules, validation, and audit logs.

## Decision

Add a guarded `draft_script` AI tool.

- It writes only under `scripts/`.
- It accepts either structured `steps` or full `yaml`, not both.
- It validates the written script immediately.
- It refuses `profile.adb_path`; private emulator paths must stay in ignored local config.
- It does not touch ADB or the emulator.
- It runs through `AgentSession`, consuming step budget and writing audit logs.

## Request Shape

```json
{
  "tool": "draft_script",
  "args": {
    "script": "scripts/ai-draft.yml",
    "steps": [
      {
        "type": "wait",
        "seconds": 0
      },
      {
        "type": "tap",
        "x": 100,
        "y": 200,
        "label": "open daily panel"
      }
    ]
  }
}
```

## Safety

- The tool must reject paths outside `scripts/`.
- The tool must reject non-YAML extensions.
- The tool must reject overwrite unless `overwrite=true`.
- The tool must reject `profile.adb_path`.
- The tool must return validation issues so humans and AI can fix drafts before dry-run.

## Acceptance Criteria

- `draft_script` is listed in `ai-schemas`.
- `draft_script` has an `ai-examples` request.
- `AiBridge.handle(...)` can write a valid draft under a configured script root.
- Attempts outside the script root are blocked.
- The call is audited through `AgentSession`.
- Unit tests cover valid draft, unsafe path, private `adb_path`, schema, and example exposure.
