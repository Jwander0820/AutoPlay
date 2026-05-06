from __future__ import annotations

import json
from typing import Any


AI_TOOL_EXAMPLES: tuple[dict[str, Any], ...] = (
    {
        "name": "doctor",
        "description": "Check whether AutoPlay can reach the configured emulator through ADB.",
        "safety": "read_only",
        "request": {"tool": "doctor", "args": {}},
    },
    {
        "name": "screenshot",
        "description": "Capture the current emulator screen into the artifact directory.",
        "safety": "read_only_device",
        "request": {"tool": "screenshot", "args": {"out": "artifacts/ai/current.png"}},
    },
    {
        "name": "dry_run_tap",
        "description": "Preview a tap command without touching the emulator.",
        "safety": "dry_run",
        "request": {"tool": "tap", "args": {"x": 100, "y": 200, "label": "open daily panel"}},
    },
    {
        "name": "guarded_real_tap",
        "description": "Send a real tap only when the server/session allows device input and the visible session code is supplied.",
        "safety": "device_input_guarded",
        "request": {
            "tool": "tap",
            "args": {
                "x": 100,
                "y": 200,
                "label": "open daily panel",
                "execute": True,
                "device_input_code": "CODE-SHOWN-IN-LAUNCHER",
            },
        },
    },
    {
        "name": "dry_run_scroll",
        "description": "Preview a scroll command without touching the emulator.",
        "safety": "dry_run",
        "request": {
            "tool": "scroll",
            "args": {"direction": "down", "distance": 700, "duration_ms": 400, "label": "inspect next task"},
        },
    },
    {
        "name": "validate_script",
        "description": "Validate a reviewable AutoPlay YAML script without touching the emulator.",
        "safety": "read_only_files",
        "request": {"tool": "validate", "args": {"script": "scripts/ldplayer-test.yml"}},
    },
    {
        "name": "draft_script",
        "description": "Write a reviewable YAML draft under scripts/ without touching the emulator.",
        "safety": "write_reviewable_script",
        "request": {
            "tool": "draft_script",
            "args": {
                "script": "scripts/ai-draft.yml",
                "steps": [
                    {"type": "wait", "seconds": 0},
                    {"type": "tap", "x": 100, "y": 200, "label": "open daily panel"},
                ],
            },
        },
    },
    {
        "name": "dry_run_script",
        "description": "Run a YAML script with device input kept dry-run and write a JSON report under artifacts.",
        "safety": "dry_run",
        "request": {
            "tool": "run_script",
            "args": {
                "script": "scripts/ldplayer-test.yml",
                "report_out": "artifacts/ai/ldplayer-test-report.json",
                "intent": "local ai dry-run script test",
            },
        },
    },
)


def get_ai_examples_payload() -> dict[str, Any]:
    return {"ok": True, "examples": [_clone(example) for example in AI_TOOL_EXAMPLES]}


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value))
