from __future__ import annotations

import io
import json
from dataclasses import dataclass
from typing import Any

from .ai_examples import get_ai_examples_payload
from .ai_mcp import MCP_PROTOCOL_VERSION, McpStdioConfig, run_mcp_stdio


class AiMcpSmokeError(RuntimeError):
    pass


@dataclass(frozen=True)
class AiMcpSmokeResult:
    protocol_version: str | None
    tool_count: int
    example_name: str | None = None
    tool_response: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        if not self.protocol_version:
            return False
        if self.tool_count <= 0:
            return False
        if self.tool_response is None:
            return True
        return not bool(self.tool_response.get("isError", False))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ok": self.ok,
            "protocol_version": self.protocol_version,
            "tool_count": self.tool_count,
        }
        if self.example_name is not None:
            data["example_name"] = self.example_name
        if self.tool_response is not None:
            data["tool_response"] = self.tool_response
        return data


def run_ai_mcp_smoke(
    config: McpStdioConfig | None = None,
    example_name: str | None = None,
    allow_real_examples: bool = False,
) -> AiMcpSmokeResult:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "autoplay-mcp-smoke", "version": "0.1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    if example_name:
        example = _find_example(example_name)
        if _is_guarded_real_example(example) and not allow_real_examples:
            raise AiMcpSmokeError(f"Example '{example_name}' can request real device input; pass --allow-real-examples to run it.")
        messages.append(_tool_call_message(3, example))

    responses = _run_stdio_messages(messages, config or McpStdioConfig())
    initialize = _response_by_id(responses, 1)
    tools = _response_by_id(responses, 2)
    call = _response_by_id(responses, 3) if example_name else None
    return AiMcpSmokeResult(
        protocol_version=initialize.get("result", {}).get("protocolVersion"),
        tool_count=len(tools.get("result", {}).get("tools", [])),
        example_name=example_name,
        tool_response=call.get("result") if call else None,
    )


def _run_stdio_messages(messages: list[dict[str, Any]], config: McpStdioConfig) -> list[dict[str, Any]]:
    stdin = io.BytesIO()
    for message in messages:
        stdin.write(json.dumps(message, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n")
    stdin.seek(0)
    stdout = io.BytesIO()
    run_mcp_stdio(config=config, input_stream=stdin, output_stream=stdout)
    responses = []
    for line in stdout.getvalue().decode("utf-8").splitlines():
        payload = json.loads(line)
        if isinstance(payload, dict):
            responses.append(payload)
    return responses


def _response_by_id(responses: list[dict[str, Any]], response_id: int) -> dict[str, Any]:
    for response in responses:
        if response.get("id") == response_id:
            return response
    raise AiMcpSmokeError(f"MCP smoke response missing id {response_id}.")


def _find_example(name: str) -> dict[str, Any]:
    for example in get_ai_examples_payload()["examples"]:
        if example.get("name") == name:
            request = example.get("request")
            if not isinstance(request, dict):
                raise AiMcpSmokeError(f"Example '{name}' does not contain a request object.")
            return example
    raise AiMcpSmokeError(f"Example not found: {name}")


def _tool_call_message(request_id: int, example: dict[str, Any]) -> dict[str, Any]:
    request = example["request"]
    tool = request["tool"]
    args = request.get("args") or {}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": f"autoplay.{tool}", "arguments": args},
    }


def _is_guarded_real_example(example: dict[str, Any]) -> bool:
    request = example.get("request")
    if not isinstance(request, dict):
        return False
    args = request.get("args")
    if not isinstance(args, dict):
        return False
    return bool(args.get("execute", args.get("execute_taps", False)))
