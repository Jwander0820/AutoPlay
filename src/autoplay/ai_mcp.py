from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from . import __version__
from .ai_adapter import get_ai_adapter_manifest, handle_adapter_call
from .ai_bridge import AiBridge


MCP_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_MCP_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")


@dataclass(frozen=True)
class McpStdioConfig:
    artifact_root: Path = Path("artifacts")
    audit_path: Path | None = None
    step_budget: int = 20
    allow_device_input: bool = False
    device_input_code: str | None = None
    adb_path: str | None = None
    serial: str | None = None


def get_mcp_tools(prefix_names: bool = True) -> list[dict[str, Any]]:
    manifest = get_ai_adapter_manifest(prefix_names=prefix_names)
    tools = []
    for tool in manifest["tools"]:
        tools.append(
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
                "annotations": tool["annotations"],
                "_meta": {
                    "autoplay/safety": tool["safety"],
                    "autoplay/bridgeTool": tool["bridge_request"]["tool"],
                },
            }
        )
    return tools


def handle_mcp_message(message: dict[str, Any], bridge: AiBridge) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return _error_response(request_id, -32600, "MCP message requires a method.")
    if "id" not in message:
        return _handle_notification(method)
    try:
        params = message.get("params", {})
        if params is None:
            params = {}
        result = _dispatch_request(method, params, bridge)
    except ValueError as exc:
        return _error_response(request_id, -32602, str(exc))
    except NotImplementedError as exc:
        return _error_response(request_id, -32601, str(exc))
    except Exception as exc:
        return _error_response(request_id, -32603, str(exc))
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def run_mcp_stdio(
    config: McpStdioConfig | None = None,
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
) -> int:
    server_config = config or McpStdioConfig()
    bridge = AiBridge.from_local_config(
        artifact_root=server_config.artifact_root,
        audit_path=server_config.audit_path,
        step_budget=server_config.step_budget,
        allow_device_input=server_config.allow_device_input,
        device_input_code=server_config.device_input_code,
        adb_path=server_config.adb_path,
        serial=server_config.serial,
    )
    stdin = input_stream or sys.stdin.buffer
    stdout = output_stream or sys.stdout.buffer
    for raw_line in stdin:
        line = _decode_line(raw_line)
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_message(stdout, _error_response(None, -32700, f"Invalid JSON: {exc}"))
            continue
        if not isinstance(message, dict):
            _write_message(stdout, _error_response(None, -32600, "MCP message must be a JSON object."))
            continue
        response = handle_mcp_message(message, bridge)
        if response is not None:
            _write_message(stdout, response)
    return 0


def _dispatch_request(method: str, params: dict[str, Any], bridge: AiBridge) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ValueError("MCP request params must be an object.")
    if method == "initialize":
        return _initialize_result(params)
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": get_mcp_tools(prefix_names=True)}
    if method == "tools/call":
        return _call_tool_result(params, bridge)
    raise NotImplementedError(f"Unsupported MCP method: {method}")


def _initialize_result(params: dict[str, Any]) -> dict[str, Any]:
    requested = params.get("protocolVersion")
    protocol_version = requested if requested in SUPPORTED_MCP_PROTOCOL_VERSIONS else MCP_PROTOCOL_VERSION
    return {
        "protocolVersion": protocol_version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {
            "name": "autoplay",
            "title": "AutoPlay Local AI Tools",
            "version": __version__,
            "description": "Safe local Android emulator automation tools.",
        },
        "instructions": "Use draft_script, validate, and dry-run run_script before requesting guarded real device input.",
    }


def _call_tool_result(params: dict[str, Any], bridge: AiBridge) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str):
        raise ValueError("tools/call requires params.name.")
    if not isinstance(arguments, dict):
        raise ValueError("tools/call params.arguments must be an object.")
    response = handle_adapter_call(bridge, name, arguments)
    text = json.dumps(response, indent=2, sort_keys=True)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": response,
        "isError": not bool(response.get("ok")),
    }


def _handle_notification(method: str) -> None:
    if method == "notifications/initialized":
        return None
    return None


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _decode_line(raw_line: bytes | str) -> str:
    if isinstance(raw_line, bytes):
        return raw_line.decode("utf-8").strip()
    return raw_line.strip()


def _write_message(output_stream: BinaryIO | TextIO, message: dict[str, Any]) -> None:
    encoded = (json.dumps(message, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    try:
        output_stream.write(encoded)  # type: ignore[arg-type]
    except TypeError:
        output_stream.write(encoded.decode("utf-8"))  # type: ignore[arg-type]
    output_stream.flush()
