from __future__ import annotations

import json
from typing import Any


SCHEMA_VERSION = "2026-05-05"


def _input_args(required: list[str], typed_properties: dict[str, str], default_label: str) -> dict[str, Any]:
    properties: dict[str, Any] = {
        name: {"type": type_name, "minimum": 0}
        for name, type_name in typed_properties.items()
    }
    properties["label"] = {"type": "string", "default": default_label}
    properties["execute"] = {"type": "boolean", "default": False}
    properties["device_input_code"] = {
        "type": "string",
        "description": "Required for real input when the bridge/server was started with a device input code.",
    }
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": False,
    }


AI_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "doctor": {
        "description": "Check emulator and ADB readiness.",
        "safety": "read_only",
        "args_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "screenshot": {
        "description": "Capture a PNG screenshot under the artifact root.",
        "safety": "read_only_device",
        "args_schema": {
            "type": "object",
            "properties": {"out": {"type": "string", "description": "Output PNG path under artifacts/."}},
            "additionalProperties": False,
        },
    },
    "match": {
        "description": "Run template matching between artifact PNG files.",
        "safety": "read_only_files",
        "args_schema": {
            "type": "object",
            "required": ["source", "template"],
            "properties": {
                "source": {"type": "string"},
                "template": {"type": "string"},
                "threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.95},
                "tolerance": {"type": "integer", "minimum": 0, "maximum": 255, "default": 0},
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "[x, y, width, height]",
                },
            },
            "additionalProperties": False,
        },
    },
    "tap": {
        "description": "Tap a coordinate. Dry-run unless args.execute=true and server/session policy allows real input.",
        "safety": "device_input_guarded",
        "args_schema": _input_args(["x", "y"], {"x": "integer", "y": "integer"}, "ai tap"),
    },
    "swipe": {
        "description": "Swipe between two coordinates. Dry-run unless explicitly allowed.",
        "safety": "device_input_guarded",
        "args_schema": _input_args(
            ["x1", "y1", "x2", "y2"],
            {"x1": "integer", "y1": "integer", "x2": "integer", "y2": "integer", "duration_ms": "integer"},
            "ai swipe",
        ),
    },
    "drag": {
        "description": "Drag between two coordinates. Dry-run unless explicitly allowed.",
        "safety": "device_input_guarded",
        "args_schema": _input_args(
            ["x1", "y1", "x2", "y2"],
            {"x1": "integer", "y1": "integer", "x2": "integer", "y2": "integer", "duration_ms": "integer"},
            "ai drag",
        ),
    },
    "scroll": {
        "description": "Scroll in one direction. Dry-run unless explicitly allowed.",
        "safety": "device_input_guarded",
        "args_schema": {
            "type": "object",
            "required": ["direction"],
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "label": {"type": "string", "default": "ai scroll"},
                "distance": {"type": "integer", "minimum": 1},
                "duration_ms": {"type": "integer", "default": 400},
                "execute": {"type": "boolean", "default": False},
                "device_input_code": {
                    "type": "string",
                    "description": "Required for real input when the bridge/server was started with a device input code.",
                },
            },
            "additionalProperties": False,
        },
    },
    "back": {
        "description": "Send Android back. Dry-run unless explicitly allowed.",
        "safety": "device_input_guarded",
        "args_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "ai back"},
                "execute": {"type": "boolean", "default": False},
                "device_input_code": {
                    "type": "string",
                    "description": "Required for real input when the bridge/server was started with a device input code.",
                },
            },
            "additionalProperties": False,
        },
    },
    "validate": {
        "description": "Validate a reviewable AutoPlay YAML script without touching the device.",
        "safety": "read_only_files",
        "args_schema": {
            "type": "object",
            "required": ["script"],
            "properties": {"script": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    "draft_script": {
        "description": "Write a reviewable AutoPlay YAML script draft under scripts/ without touching the device.",
        "safety": "write_reviewable_script",
        "args_schema": {
            "type": "object",
            "required": ["script"],
            "properties": {
                "script": {"type": "string", "description": "Output path under scripts/ with .yml or .yaml extension."},
                "steps": {"type": "array", "items": {"type": "object"}, "description": "Structured AutoPlay step objects."},
                "yaml": {"type": "string", "description": "Full YAML script text. Mutually exclusive with steps."},
                "profile": {
                    "type": "object",
                    "properties": {"serial": {"type": "string"}},
                    "additionalProperties": False,
                    "description": "Optional non-private profile metadata. adb_path is intentionally not accepted.",
                },
                "overwrite": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
    },
    "run_script": {
        "description": "Validate and run a YAML script. Device input remains dry-run unless explicitly allowed.",
        "safety": "device_input_guarded",
        "args_schema": {
            "type": "object",
            "required": ["script"],
            "properties": {
                "script": {"type": "string"},
                "report_out": {"type": "string", "description": "JSON report path under artifacts/."},
                "intent": {"type": "string", "default": "local ai requested script run"},
                "execute": {"type": "boolean", "default": False},
                "execute_taps": {"type": "boolean", "default": False},
                "device_input_code": {
                    "type": "string",
                    "description": "Required for real input when the bridge/server was started with a device input code.",
                },
            },
            "additionalProperties": False,
        },
    },
}

SUPPORTED_TOOLS = tuple(AI_TOOL_SCHEMAS)


def get_ai_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": schema["description"],
            "safety": schema["safety"],
            "args_schema": _clone(schema["args_schema"]),
            "request_schema": _request_schema(name, schema["args_schema"]),
        }
        for name, schema in AI_TOOL_SCHEMAS.items()
    ]


def get_ai_schema_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "request_shape": {"tool": "<tool name>", "args": {}},
        "response_shape": {"ok": True, "tool": "<tool name>", "result": {}, "messages": [], "steps_remaining": 0},
        "tools": get_ai_tool_schemas(),
    }


def _request_schema(tool: str, args_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["tool"],
        "properties": {
            "tool": {"const": tool},
            "args": _clone(args_schema),
        },
        "additionalProperties": False,
    }


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value))
