from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_client import AiClientError, run_ai_client_smoke
from autoplay.ai_server import AiToolServerConfig, create_ai_tool_server


class AiClientTest(unittest.TestCase):
    def test_smoke_reads_contract_without_running_tool(self):
        ready = create_ai_tool_server(AiToolServerConfig(port=0))
        thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
        thread.start()
        try:
            result = run_ai_client_smoke(ready.url)
        finally:
            ready.server.shutdown()
            ready.server.server_close()
            thread.join(timeout=2)

        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.schema_count, 1)
        self.assertGreaterEqual(result.example_count, 1)
        self.assertIsNone(result.tool_response)

    def test_smoke_can_post_dry_run_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            ready = create_ai_tool_server(AiToolServerConfig(port=0, artifact_root=root))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)):
                    result = run_ai_client_smoke(ready.url, example_name="dry_run_tap")
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

        self.assertTrue(result.ok)
        self.assertEqual(result.example_name, "dry_run_tap")
        self.assertEqual(result.tool_response["tool"], "tap")
        self.assertTrue(result.tool_response["result"]["dry_run"])

    def test_smoke_rejects_guarded_real_example_by_default(self):
        ready = create_ai_tool_server(AiToolServerConfig(port=0))
        thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaisesRegex(AiClientError, "real device input"):
                run_ai_client_smoke(ready.url, example_name="guarded_real_tap")
        finally:
            ready.server.shutdown()
            ready.server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
