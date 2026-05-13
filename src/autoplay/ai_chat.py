from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

from .ai_bridge import AiBridge, AiBridgeConfig
from .ai_schemas import SUPPORTED_TOOLS, get_ai_tool_schemas


class AiChatError(RuntimeError):
    pass


@dataclass(frozen=True)
class AiChatConfig:
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    timeout: float = 60.0
    max_tool_calls: int = 4
    allowed_tools: tuple[str, ...] | None = None


@dataclass(frozen=True)
class AiChatResult:
    ok: bool
    provider: str
    model: str
    final_message: str
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    incomplete: bool = False
    transcript: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "model": self.model,
            "final_message": self.final_message,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "incomplete": self.incomplete,
            "transcript": self.transcript or [],
        }


def run_ai_chat(
    prompt: str,
    chat_config: AiChatConfig,
    bridge_config: AiBridgeConfig | None = None,
    bridge: AiBridge | None = None,
) -> AiChatResult:
    if not prompt.strip():
        raise AiChatError("ai-chat requires a non-empty prompt.")
    client = _client_for_config(chat_config)
    bridge = bridge or AiBridge(bridge_config or AiBridgeConfig())
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": prompt},
    ]
    allowed_tools = _normalize_allowed_tools(chat_config.allowed_tools)
    tools = get_chat_tool_definitions(allowed_tools=allowed_tools)
    allowed_tool_names = {tool["function"]["name"] for tool in tools}
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    transcript: list[dict[str, Any]] = []
    final_message = ""
    incomplete = False
    max_tool_calls = max(chat_config.max_tool_calls, 0)

    for turn in range(1, max_tool_calls + 2):
        transcript.append(
            {
                "type": "request",
                "turn": turn,
                "provider": client.provider,
                "model": client.model,
                "message_count": len(messages),
                "tools": [tool["function"]["name"] for tool in tools],
            }
        )
        response_message = client.chat(messages, tools)
        final_message = str(response_message.get("content") or "")
        calls = _extract_tool_calls(response_message)
        transcript.append(
            {
                "type": "assistant",
                "turn": turn,
                "content": final_message,
                "tool_calls": _redact_local_paths(calls),
            }
        )
        if not calls:
            break
        if len(tool_calls) >= max_tool_calls:
            incomplete = True
            final_message = "Tool call limit reached before all requested tool calls were executed."
            break
        messages.append(_assistant_message_for_history(response_message, client.provider))
        for call in calls:
            if call["name"] not in allowed_tool_names:
                raise AiChatError(f"Tool call '{call['name']}' is not allowed in this chat session.")
            if len(tool_calls) >= max_tool_calls:
                incomplete = True
                final_message = "Tool call limit reached before all requested tool calls were executed."
                break
            tool_calls.append(call)
            result = bridge.handle({"tool": call["name"], "args": call["arguments"]})
            tool_results.append(result)
            transcript.append(
                {
                    "type": "tool_result",
                    "turn": turn,
                    "tool": call["name"],
                    "result": _redact_local_paths(_model_safe_tool_result(result)),
                }
            )
            messages.append(_tool_result_message(call, result, client.provider))
        if incomplete:
            break

    return AiChatResult(
        ok=(not incomplete) and all(bool(result.get("ok")) for result in tool_results),
        provider=client.provider,
        model=client.model,
        final_message=final_message,
        tool_calls=tool_calls,
        tool_results=tool_results,
        incomplete=incomplete,
        transcript=transcript,
    )


def get_chat_tool_definitions(allowed_tools: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    normalized_allowed = _normalize_allowed_tools(allowed_tools)
    allowed = set(normalized_allowed) if normalized_allowed is not None else None
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["args_schema"],
            },
        }
        for tool in get_ai_tool_schemas()
        if allowed is None or tool["name"] in allowed
    ]


class _ChatClient:
    def __init__(self, config: AiChatConfig):
        self.provider = _normalize_provider(config.provider)
        self.model = config.model
        self.base_url = _base_url_for_provider(self.provider, config.base_url)
        self.api_key = config.api_key or _api_key_for_provider(self.provider)
        self.temperature = config.temperature
        self.timeout = config.timeout
        if self.provider == "openai" and not self.api_key:
            raise AiChatError("OpenAI provider requires --api-key or OPENAI_API_KEY.")

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self.provider == "fake":
            return self._fake_chat(messages, tools)
        if self.provider == "ollama":
            return self._ollama_chat(messages, tools)
        return self._openai_compatible_chat(messages, tools)

    def _openai_compatible_chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": self.temperature,
            "stream": False,
        }
        response = _post_json(
            _openai_compatible_chat_url(self.base_url),
            payload,
            timeout=self.timeout,
            api_key=self.api_key,
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AiChatError("Chat completion response did not include choices.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise AiChatError("Chat completion choice did not include a message object.")
        return message

    def _ollama_chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": _ollama_messages(messages),
            "tools": tools,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        response = _post_json(_ollama_chat_url(self.base_url), payload, timeout=self.timeout)
        message = response.get("message")
        if not isinstance(message, dict):
            raise AiChatError("Ollama response did not include a message object.")
        return message

    def _fake_chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self.model != "draft_script":
            raise AiChatError(f"Unknown fake ai-chat model: {self.model}")
        if any(message.get("role") == "tool" for message in messages):
            return {"role": "assistant", "content": "fake provider completed draft_script"}
        tool_names = {tool["function"]["name"] for tool in tools}
        if "draft_script" not in tool_names:
            raise AiChatError("Fake draft_script smoke requires the draft_script tool.")
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "fake-call-1",
                    "type": "function",
                    "function": {
                        "name": "draft_script",
                        "arguments": {
                            "script": _fake_script_path(messages),
                            "steps": [{"type": "wait", "seconds": 0}],
                            "overwrite": True,
                        },
                    },
                }
            ],
        }


def _client_for_config(config: AiChatConfig) -> _ChatClient:
    if not config.model.strip():
        raise AiChatError("ai-chat requires a model name.")
    return _ChatClient(config)


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower().replace("_", "-")
    aliases = {"lm-studio": "lmstudio", "openai-compatible": "lmstudio"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"fake", "ollama", "lmstudio", "openai"}:
        raise AiChatError("provider must be one of: fake, ollama, lmstudio, openai.")
    return normalized


def _base_url_for_provider(provider: str, base_url: str | None) -> str:
    if base_url:
        return base_url
    defaults = {
        "ollama": "http://127.0.0.1:11434",
        "lmstudio": "http://127.0.0.1:1234/v1",
        "openai": "https://api.openai.com/v1",
        "fake": "memory://ai-chat-smoke",
    }
    return defaults[provider]


def _fake_script_path(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "")
        marker = "script:"
        if marker in content:
            candidate = content.split(marker, 1)[1].strip().split()[0]
            if candidate:
                return candidate
    return "scripts/ai-chat-smoke.yml"


def _openai_compatible_chat_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return normalized + "/chat/completions"


def _ollama_chat_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/api/chat"):
        return normalized
    return normalized + "/api/chat"


def _api_key_for_provider(provider: str) -> str | None:
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    if provider == "lmstudio":
        return os.environ.get("LMSTUDIO_API_KEY")
    return None


def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    raw_calls = message.get("tool_calls")
    if not isinstance(raw_calls, list):
        return []
    calls = []
    for index, raw_call in enumerate(raw_calls):
        if not isinstance(raw_call, dict):
            continue
        function = raw_call.get("function")
        if not isinstance(function, dict):
            continue
        name = _normalize_tool_call_name(function.get("name"))
        if not isinstance(name, str) or not name:
            continue
        calls.append(
            {
                "id": str(raw_call.get("id") or f"tool-{index + 1}"),
                "name": name,
                "arguments": _parse_tool_arguments(function.get("arguments")),
            }
        )
    return calls


def _parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        if not arguments.strip():
            return {}
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise AiChatError(f"Invalid tool arguments JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise AiChatError("Tool arguments JSON must decode to an object.")
        return parsed
    raise AiChatError("Tool arguments must be an object or JSON object string.")


def _normalize_tool_call_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()
    if name.startswith("autoplay."):
        name = name.removeprefix("autoplay.")
    return name


def _normalize_allowed_tools(allowed_tools: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if allowed_tools is None:
        return None
    normalized = []
    for tool in allowed_tools:
        name = _normalize_tool_call_name(tool)
        if not name or name not in SUPPORTED_TOOLS:
            raise AiChatError(f"Unknown allowed tool: {tool}")
        if name not in normalized:
            normalized.append(name)
    return tuple(normalized)


def _assistant_message_for_history(message: dict[str, Any], provider: str) -> dict[str, Any]:
    if provider == "ollama":
        return {"role": "assistant", "content": str(message.get("content") or ""), "tool_calls": message.get("tool_calls") or []}
    return {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls") or [],
    }


def _tool_result_message(call: dict[str, Any], result: dict[str, Any], provider: str) -> dict[str, Any]:
    content = json.dumps(_model_safe_tool_result(result), sort_keys=True)
    if provider == "ollama":
        return {"role": "tool", "content": content}
    return {"role": "tool", "tool_call_id": call["id"], "content": content}


def _model_safe_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    safe = json.loads(json.dumps(result))
    result_payload = safe.get("result")
    if isinstance(result_payload, dict) and "command" in result_payload:
        result_payload["command"] = "<redacted-local-command>"
    return safe


def _redact_local_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_local_paths(part) for key, part in value.items()}
    if isinstance(value, list):
        return [_redact_local_paths(part) for part in value]
    if isinstance(value, str):
        if ":\\" in value or ":/" in value:
            return "<redacted-local-path>"
        return value
    return value


def _ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for message in messages:
        item = {key: value for key, value in message.items() if key in {"role", "content", "tool_calls"}}
        if item.get("content") is None:
            item["content"] = ""
        normalized.append(item)
    return normalized


def _post_json(url: str, payload: dict[str, Any], timeout: float, api_key: str | None = None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return _decode_json(response.read())
    except OSError as exc:
        raise AiChatError(f"Cannot POST {url}: {exc}") from exc


def _decode_json(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AiChatError(f"Invalid JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise AiChatError("JSON response must be an object.")
    return payload


def _system_prompt() -> str:
    return (
        "You are AutoPlay's local automation assistant. Prefer this safe workflow: "
        "draft_script, validate, dry-run run_script, then human review before any real device input. "
        "Do not set execute=true unless the user explicitly asks for real device input and the session is configured for it. "
        "Use tools only for bounded, auditable Android emulator automation tasks."
    )
