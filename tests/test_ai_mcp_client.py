from pathlib import Path
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_mcp import McpStdioConfig
from autoplay.ai_mcp_client import AiMcpSmokeError, run_ai_mcp_smoke


class AiMcpClientTest(unittest.TestCase):
    def test_smoke_checks_initialize_and_tool_list_without_running_tool(self):
        result = run_ai_mcp_smoke()

        self.assertTrue(result.ok)
        self.assertEqual(result.protocol_version, "2025-11-25")
        self.assertGreaterEqual(result.tool_count, 1)
        self.assertIsNone(result.tool_response)

    def test_smoke_can_call_dry_run_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            config = McpStdioConfig(artifact_root=root, audit_path=root / "agent" / "mcp-smoke.jsonl")
            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)):
                result = run_ai_mcp_smoke(config=config, example_name="dry_run_tap")

        self.assertTrue(result.ok)
        self.assertEqual(result.example_name, "dry_run_tap")
        self.assertFalse(result.tool_response["isError"])
        self.assertTrue(result.tool_response["structuredContent"]["result"]["dry_run"])

    def test_smoke_rejects_guarded_real_example_by_default(self):
        with self.assertRaisesRegex(AiMcpSmokeError, "real device input"):
            run_ai_mcp_smoke(example_name="guarded_real_tap")

    def test_smoke_reports_missing_example(self):
        with self.assertRaisesRegex(AiMcpSmokeError, "Example not found"):
            run_ai_mcp_smoke(example_name="missing")


if __name__ == "__main__":
    unittest.main()
