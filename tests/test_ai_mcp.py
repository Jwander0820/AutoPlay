import io
import json
import unittest
from pathlib import Path
import tempfile
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_bridge import AiBridge, AiBridgeConfig
from autoplay.ai_mcp import MCP_PROTOCOL_VERSION, get_mcp_tools, handle_mcp_message, run_mcp_stdio


class AiMcpTest(unittest.TestCase):
    def test_initialize_returns_tools_capability(self):
        bridge = mock.Mock()

        response = handle_mcp_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            },
            bridge,
        )

        self.assertEqual(response["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertIn("tools", response["result"]["capabilities"])
        self.assertEqual(response["result"]["serverInfo"]["name"], "autoplay")

    def test_tools_list_uses_prefixed_adapter_tools(self):
        bridge = mock.Mock()

        response = handle_mcp_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, bridge)

        tools = {tool["name"]: tool for tool in response["result"]["tools"]}
        self.assertIn("autoplay.tap", tools)
        self.assertIn("inputSchema", tools["autoplay.tap"])
        self.assertEqual(tools["autoplay.tap"]["_meta"]["autoplay/bridgeTool"], "tap")

    def test_tools_call_routes_through_ai_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            bridge = AiBridge(AiBridgeConfig(artifact_root=root, audit_path=root / "agent" / "mcp.jsonl"))
            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)):
                response = handle_mcp_message(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "autoplay.tap", "arguments": {"x": 1, "y": 2, "label": "open menu"}},
                    },
                    bridge,
                )

        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertTrue(result["structuredContent"]["ok"])
        self.assertEqual(result["structuredContent"]["tool"], "tap")
        self.assertEqual(result["content"][0]["type"], "text")

    def test_tool_failure_is_returned_as_call_result_error(self):
        bridge = mock.Mock()
        bridge.handle.return_value = {"ok": False, "tool": "tap", "messages": ["blocked"]}

        response = handle_mcp_message(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "tap", "arguments": {"x": 1, "y": 2}}},
            bridge,
        )

        self.assertTrue(response["result"]["isError"])
        self.assertEqual(response["result"]["structuredContent"]["messages"], ["blocked"])

    def test_unknown_method_returns_json_rpc_error(self):
        response = handle_mcp_message({"jsonrpc": "2.0", "id": 5, "method": "missing"}, mock.Mock())

        self.assertEqual(response["error"]["code"], -32601)
        self.assertIn("Unsupported MCP method", response["error"]["message"])

    def test_non_object_params_return_invalid_params(self):
        response = handle_mcp_message({"jsonrpc": "2.0", "id": 6, "method": "tools/list", "params": []}, mock.Mock())

        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("params must be an object", response["error"]["message"])

    def test_initialized_notification_has_no_response(self):
        response = handle_mcp_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, mock.Mock())

        self.assertIsNone(response)

    def test_stdio_server_reads_newline_delimited_json_rpc(self):
        input_stream = io.BytesIO(
            b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'
            b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        )
        output_stream = io.BytesIO()

        self.assertEqual(run_mcp_stdio(input_stream=input_stream, output_stream=output_stream), 0)

        lines = [json.loads(line) for line in output_stream.getvalue().decode("utf-8").splitlines()]
        self.assertEqual(len(lines), 1)
        self.assertIn("tools", lines[0]["result"])

    def test_mcp_tools_are_schema_shaped(self):
        tap = next(tool for tool in get_mcp_tools() if tool["name"] == "autoplay.tap")

        self.assertEqual(tap["inputSchema"]["type"], "object")
        self.assertFalse(tap["annotations"]["destructiveHint"])


if __name__ == "__main__":
    unittest.main()
