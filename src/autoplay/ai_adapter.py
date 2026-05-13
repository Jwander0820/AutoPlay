from __future__ import annotations

import json
from typing import Any

from .ai_schemas import SCHEMA_VERSION, SUPPORTED_TOOLS, get_ai_tool_schemas


ADAPTER_VERSION = "2026-05-13"
ADAPTER_PREFIX = "autoplay."


def get_ai_adapter_manifest(prefix_names: bool = False) -> dict[str, Any]:
    tools = [_adapter_tool(schema, prefix_names=prefix_names) for schema in get_ai_tool_schemas()]
    return {
        "ok": True,
        "adapter_version": ADAPTER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "bridge_contract": {"request": {"tool": "<tool name>", "args": {}}, "call_path": "AiBridge -> AgentSession -> api.py"},
        "tools": tools,
    }


def adapter_call_request(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    tool = _normalize_tool_name(name)
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("adapter call arguments must be a JSON object.")
    return {"tool": tool, "args": arguments}


def handle_adapter_call(bridge: Any, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return bridge.handle(adapter_call_request(name, arguments))


def get_ai_adapter_payload(prefix_names: bool = False) -> dict[str, Any]:
    return json.loads(json.dumps(get_ai_adapter_manifest(prefix_names=prefix_names)))


def _adapter_tool(schema: dict[str, Any], prefix_names: bool) -> dict[str, Any]:
    name = schema["name"]
    safety = schema["safety"]
    return {
        "name": f"{ADAPTER_PREFIX}{name}" if prefix_names else name,
        "description": schema["description"],
        "inputSchema": schema["args_schema"],
        "safety": safety,
        "annotations": _annotations_for_safety(safety),
        "bridge_request": {"tool": name, "args": "<arguments>"},
    }


def _annotations_for_safety(safety: str) -> dict[str, bool]:
    read_only = safety in {"read_only", "read_only_files", "read_only_device"}
    return {
        "readOnlyHint": read_only,
        "destructiveHint": False,
        "idempotentHint": read_only,
        "openWorldHint": safety in {"read_only_device", "device_input_guarded"},
    }


def _normalize_tool_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("adapter call requires a non-empty tool name.")
    tool = name.strip()
    if tool.startswith(ADAPTER_PREFIX):
        tool = tool.removeprefix(ADAPTER_PREFIX)
    if tool not in SUPPORTED_TOOLS:
        raise ValueError(f"Unknown adapter tool: {name}. Supported tools: {', '.join(SUPPORTED_TOOLS)}")
    return tool
