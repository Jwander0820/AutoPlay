from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request


class AiClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class AiClientSmokeResult:
    base_url: str
    health: dict[str, Any]
    schema_count: int
    example_count: int
    example_name: str | None = None
    tool_response: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        if not self.health.get("ok"):
            return False
        if self.tool_response is None:
            return True
        return bool(self.tool_response.get("ok"))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "ok": self.ok,
            "base_url": self.base_url,
            "health": self.health,
            "schema_count": self.schema_count,
            "example_count": self.example_count,
        }
        if self.example_name is not None:
            data["example_name"] = self.example_name
        if self.tool_response is not None:
            data["tool_response"] = self.tool_response
        return data


def run_ai_client_smoke(
    base_url: str = "http://127.0.0.1:8787",
    example_name: str | None = None,
    timeout: float = 3.0,
    allow_real_examples: bool = False,
) -> AiClientSmokeResult:
    normalized_url = _normalize_base_url(base_url)
    health = _get_json(normalized_url + "health", timeout=timeout)
    schemas = _get_json(normalized_url + "schemas", timeout=timeout)
    examples = _get_json(normalized_url + "examples", timeout=timeout)
    schema_count = len(schemas.get("tools", []))
    example_items = examples.get("examples", [])
    tool_response = None
    if example_name:
        example = _find_example(example_items, example_name)
        if _is_guarded_real_example(example) and not allow_real_examples:
            raise AiClientError(f"Example '{example_name}' can request real device input; pass --allow-real-examples to run it.")
        tool_response = _post_json(normalized_url + "tool", example["request"], timeout=timeout)
    return AiClientSmokeResult(
        base_url=normalized_url.rstrip("/"),
        health=health,
        schema_count=schema_count,
        example_count=len(example_items),
        example_name=example_name,
        tool_response=tool_response,
    )


def _normalize_base_url(base_url: str) -> str:
    if not base_url:
        raise AiClientError("base_url is required.")
    return base_url.rstrip("/") + "/"


def _find_example(examples: list[Any], name: str) -> dict[str, Any]:
    for example in examples:
        if isinstance(example, dict) and example.get("name") == name:
            request_payload = example.get("request")
            if not isinstance(request_payload, dict):
                raise AiClientError(f"Example '{name}' does not contain a request object.")
            return example
    raise AiClientError(f"Example not found: {name}")


def _is_guarded_real_example(example: dict[str, Any]) -> bool:
    request_payload = example.get("request")
    if not isinstance(request_payload, dict):
        return False
    args = request_payload.get("args")
    if not isinstance(args, dict):
        return False
    return bool(args.get("execute", args.get("execute_taps", False)))


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            return _decode_json(response.read())
    except OSError as exc:
        raise AiClientError(f"Cannot GET {url}: {exc}") from exc


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return _decode_json(response.read())
    except OSError as exc:
        raise AiClientError(f"Cannot POST {url}: {exc}") from exc


def _decode_json(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AiClientError(f"Invalid JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise AiClientError("JSON response must be an object.")
    return payload
