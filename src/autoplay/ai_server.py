from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .ai_adapter import get_ai_adapter_payload, handle_adapter_call
from .ai_bridge import SUPPORTED_TOOLS, AiBridge
from .ai_examples import get_ai_examples_payload
from .ai_schemas import SCHEMA_VERSION, get_ai_schema_payload


MAX_POST_BYTES = 1_000_000


@dataclass(frozen=True)
class AiToolServerConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    artifact_root: Path = Path("artifacts")
    audit_path: Path | None = None
    step_budget: int = 20
    allow_device_input: bool = False
    device_input_code: str | None = None
    adb_path: str | None = None
    serial: str | None = None


@dataclass(frozen=True)
class AiToolServerReady:
    server: ThreadingHTTPServer
    url: str


def create_ai_tool_server(config: AiToolServerConfig | None = None) -> AiToolServerReady:
    server_config = config or AiToolServerConfig()
    handler = _make_handler(server_config)
    server = ThreadingHTTPServer((server_config.host, server_config.port), handler)
    host, port = server.server_address
    return AiToolServerReady(server=server, url=f"http://{host}:{port}/")


def _make_handler(config: AiToolServerConfig):
    bridge = AiBridge.from_local_config(
        artifact_root=config.artifact_root,
        audit_path=config.audit_path,
        step_budget=config.step_budget,
        allow_device_input=config.allow_device_input,
        device_input_code=config.device_input_code,
        adb_path=config.adb_path,
        serial=config.serial,
    )

    class AiToolHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "autoplay-ai-tool-server",
                        "schema_version": SCHEMA_VERSION,
                        "tools": list(SUPPORTED_TOOLS),
                        "steps_remaining": bridge.session.steps_remaining,
                        "device_input": {
                            "allowed": config.allow_device_input,
                            "code_required": bool(config.allow_device_input and config.device_input_code),
                        },
                    },
                )
                return
            if self.path == "/tools":
                self._write_json(HTTPStatus.OK, {"ok": True, "schema_version": SCHEMA_VERSION, "tools": list(SUPPORTED_TOOLS)})
                return
            if self.path in {"/schemas", "/schema"}:
                self._write_json(HTTPStatus.OK, get_ai_schema_payload())
                return
            if self.path in {"/examples", "/example-requests"}:
                self._write_json(HTTPStatus.OK, get_ai_examples_payload())
                return
            if self.path in {"/adapter", "/mcp/tools"}:
                self._write_json(HTTPStatus.OK, get_ai_adapter_payload())
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "messages": ["Not found."]})

        def do_POST(self) -> None:
            if self.path not in {"/tool", "/api/tool", "/mcp/call"}:
                self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "messages": ["Not found."]})
                return
            payload = self._read_json_payload()
            if payload is None:
                return
            response = _handle_post_tool(payload)
            self._write_json(HTTPStatus.OK, response)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json_payload(self) -> dict[str, Any] | None:
            length_header = self.headers.get("Content-Length")
            try:
                length = int(length_header or "0")
            except ValueError:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["Invalid Content-Length."]})
                return None
            if length <= 0 or length > MAX_POST_BYTES:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["Invalid request size."]})
                return None
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": [f"Invalid JSON: {exc}"]})
                return None
            if not isinstance(payload, dict):
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["Request body must be a JSON object."]})
                return None
            return payload

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _handle_post_tool(payload: dict[str, Any]) -> dict[str, Any]:
        if "name" in payload or "arguments" in payload:
            try:
                arguments = payload["arguments"] if "arguments" in payload else {}
                return handle_adapter_call(bridge, str(payload.get("name") or ""), arguments)
            except Exception as exc:
                return {"ok": False, "tool": None, "result": {}, "messages": [str(exc)], "steps_remaining": bridge.session.steps_remaining}
        return bridge.handle(payload)

    return AiToolHandler
