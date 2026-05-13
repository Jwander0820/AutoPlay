from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_bridge import AiBridgeConfig
from autoplay.ai_chat import AiChatConfig, AiChatError, get_chat_tool_definitions, run_ai_chat


class AiChatTest(unittest.TestCase):
    def test_tool_definitions_use_supported_ai_schemas(self):
        tools = {tool["function"]["name"]: tool for tool in get_chat_tool_definitions()}

        self.assertIn("draft_script", tools)
        self.assertIn("run_script", tools)
        self.assertEqual(tools["tap"]["type"], "function")
        self.assertEqual(tools["tap"]["function"]["parameters"]["properties"]["execute"]["default"], False)

    def test_tool_definitions_can_be_limited_by_allowlist(self):
        tools = get_chat_tool_definitions(allowed_tools=("draft_script", "validate"))

        self.assertEqual([tool["function"]["name"] for tool in tools], ["validate", "draft_script"])

    def test_tool_definition_allowlist_rejects_unknown_tools(self):
        with self.assertRaisesRegex(AiChatError, "Unknown allowed tool"):
            get_chat_tool_definitions(allowed_tools=("raw_adb",))

    def test_openai_compatible_provider_runs_tool_call_through_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            responses = [
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "tap", "arguments": '{"x": 1, "y": 2, "label": "open menu"}'},
                                    }
                                ],
                            }
                        }
                    ]
                },
                {"choices": [{"message": {"role": "assistant", "content": "tap preview ready"}}]},
            ]
            with (
                mock.patch("autoplay.ai_chat._post_json", side_effect=responses) as post_json,
                mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)),
            ):
                result = run_ai_chat(
                    "preview a tap",
                    AiChatConfig(provider="lmstudio", model="local-model", max_tool_calls=2),
                    bridge_config=AiBridgeConfig(artifact_root=root, audit_path=root / "agent" / "chat.jsonl"),
                )

        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "lmstudio")
        self.assertEqual(result.final_message, "tap preview ready")
        self.assertEqual(result.tool_calls[0]["name"], "tap")
        self.assertTrue(result.tool_results[0]["result"]["dry_run"])
        self.assertGreaterEqual(len(result.transcript), 3)
        tool_result_events = [event for event in result.transcript if event["type"] == "tool_result"]
        self.assertEqual(tool_result_events[0]["result"]["result"]["command"], "<redacted-local-command>")
        self.assertTrue(post_json.call_args_list[0].args[0].endswith("/v1/chat/completions"))
        second_messages = post_json.call_args_list[1].args[1]["messages"]
        self.assertIn("<redacted-local-command>", second_messages[-1]["content"])
        self.assertNotIn('"command": ["adb", "tap"]', second_messages[-1]["content"])
        self.assertIsNone(post_json.call_args_list[0].kwargs["api_key"])

    def test_openai_provider_reads_api_key_from_environment(self):
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with mock.patch(
                "autoplay.ai_chat._post_json",
                return_value={"choices": [{"message": {"role": "assistant", "content": "ready"}}]},
            ) as post_json:
                result = run_ai_chat("hello", AiChatConfig(provider="openai", model="gpt-4.1-mini"))

        self.assertTrue(result.ok)
        self.assertEqual(result.final_message, "ready")
        self.assertEqual(post_json.call_args.kwargs["api_key"], "test-key")

    def test_ollama_provider_uses_ollama_chat_endpoint(self):
        responses = [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"function": {"name": "doctor", "arguments": {}}}],
                }
            },
            {"message": {"role": "assistant", "content": "doctor checked"}},
        ]
        with (
            mock.patch("autoplay.ai_chat._post_json", side_effect=responses) as post_json,
            mock.patch("autoplay.api.doctor", return_value=mock.Mock(ok=True, lines=["ADB ready"])),
        ):
            result = run_ai_chat("check device", AiChatConfig(provider="ollama", model="llama3.1"))

        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.final_message, "doctor checked")
        self.assertTrue(post_json.call_args_list[0].args[0].endswith("/api/chat"))

    def test_openai_compatible_base_url_may_be_full_chat_endpoint(self):
        with mock.patch(
            "autoplay.ai_chat._post_json",
            return_value={"choices": [{"message": {"role": "assistant", "content": "ready"}}]},
        ) as post_json:
            run_ai_chat(
                "hello",
                AiChatConfig(
                    provider="lm-studio",
                    model="loaded-model",
                    base_url="http://127.0.0.1:1234/v1/chat/completions",
                ),
            )

        self.assertEqual(post_json.call_args.args[0], "http://127.0.0.1:1234/v1/chat/completions")

    def test_ollama_base_url_may_be_full_chat_endpoint(self):
        with mock.patch("autoplay.ai_chat._post_json", return_value={"message": {"role": "assistant", "content": "ready"}}) as post_json:
            run_ai_chat(
                "hello",
                AiChatConfig(
                    provider="ollama",
                    model="llama3.1",
                    base_url="http://127.0.0.1:11434/api/chat",
                ),
            )

        self.assertEqual(post_json.call_args.args[0], "http://127.0.0.1:11434/api/chat")

    def test_openai_requires_api_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(AiChatError, "OPENAI_API_KEY"):
                run_ai_chat("hello", AiChatConfig(provider="openai", model="gpt-4.1-mini"))

    def test_bad_tool_arguments_raise_clear_error(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "tap", "arguments": "[1, 2]"},
                            }
                        ],
                    }
                }
            ]
        }
        with mock.patch("autoplay.ai_chat._post_json", return_value=response):
            with self.assertRaisesRegex(AiChatError, "must decode to an object"):
                run_ai_chat("bad args", AiChatConfig(provider="lmstudio", model="local-model"))

    def test_malformed_tool_arguments_raise_clear_error(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "tap", "arguments": "{bad json"},
                            }
                        ],
                    }
                }
            ]
        }
        with mock.patch("autoplay.ai_chat._post_json", return_value=response):
            with self.assertRaisesRegex(AiChatError, "Invalid tool arguments JSON"):
                run_ai_chat("bad args", AiChatConfig(provider="lmstudio", model="local-model"))

    def test_prefixed_tool_call_names_are_mapped_to_bridge_names(self):
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "autoplay.tap", "arguments": '{"x": 1, "y": 2}'},
                                }
                            ],
                        }
                    }
                ]
            },
            {"choices": [{"message": {"role": "assistant", "content": "ready"}}]},
        ]
        with (
            mock.patch("autoplay.ai_chat._post_json", side_effect=responses),
            mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)) as tap,
        ):
            result = run_ai_chat("tap", AiChatConfig(provider="lmstudio", model="local-model"))

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_calls[0]["name"], "tap")
        tap.assert_called_once()

    def test_disallowed_tool_call_is_rejected_before_bridge(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "tap", "arguments": '{"x": 1, "y": 2}'},
                            }
                        ],
                    }
                }
            ]
        }
        with (
            mock.patch("autoplay.ai_chat._post_json", return_value=response),
            mock.patch("autoplay.api.tap") as tap,
        ):
            with self.assertRaisesRegex(AiChatError, "not allowed"):
                run_ai_chat(
                    "tap",
                    AiChatConfig(provider="lmstudio", model="local-model", allowed_tools=("draft_script",)),
                )

        tap.assert_not_called()

    def test_tool_call_limit_marks_result_incomplete(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "tap", "arguments": '{"x": 1, "y": 2}'},
                            }
                        ],
                    }
                }
            ]
        }
        with mock.patch("autoplay.ai_chat._post_json", return_value=response):
            result = run_ai_chat("no tools", AiChatConfig(provider="lmstudio", model="local-model", max_tool_calls=0))

        self.assertFalse(result.ok)
        self.assertTrue(result.incomplete)
        self.assertIn("Tool call limit", result.final_message)

    def test_rejects_unknown_provider(self):
        with self.assertRaisesRegex(AiChatError, "provider must be"):
            run_ai_chat("hello", AiChatConfig(provider="missing", model="x"))

    def test_fake_provider_smoke_runs_draft_script_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_root = tmp_path / "scripts"
            artifact_root = tmp_path / "artifacts"

            result = run_ai_chat(
                f"draft a safe wait script script:{script_root / 'ai-chat-smoke.yml'}",
                AiChatConfig(
                    provider="fake",
                    model="draft_script",
                    allowed_tools=("draft_script",),
                    max_tool_calls=1,
                ),
                bridge_config=AiBridgeConfig(
                    artifact_root=artifact_root,
                    audit_path=artifact_root / "agent" / "fake-chat.jsonl",
                    script_root=script_root,
                ),
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "fake")
        self.assertEqual(result.tool_calls[0]["name"], "draft_script")
        self.assertEqual(result.tool_results[0]["result"]["step_count"], 1)
        self.assertEqual(result.final_message, "fake provider completed draft_script")
        transcript_text = json.dumps(result.transcript, sort_keys=True)
        self.assertNotIn(str(tmp_path), transcript_text)
        self.assertIn("<redacted-local-path>", transcript_text)

    def test_fake_provider_rejects_unknown_scenario(self):
        with self.assertRaisesRegex(AiChatError, "Unknown fake ai-chat model"):
            run_ai_chat("hello", AiChatConfig(provider="fake", model="missing"))


if __name__ == "__main__":
    unittest.main()
