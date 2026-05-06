from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib import request
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_server import AiToolServerConfig, create_ai_tool_server


class AiServerTest(unittest.TestCase):
    def test_health_and_tools_endpoints(self):
        ready = create_ai_tool_server(AiToolServerConfig(port=0))
        thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
        thread.start()
        try:
            health = _get_json(ready.url + "health")
            tools = _get_json(ready.url + "tools")
            schemas = _get_json(ready.url + "schemas")
            examples = _get_json(ready.url + "examples")
        finally:
            ready.server.shutdown()
            ready.server.server_close()
            thread.join(timeout=2)

        self.assertTrue(health["ok"])
        self.assertIn("schema_version", health)
        self.assertIn("tap", health["tools"])
        self.assertFalse(health["device_input"]["allowed"])
        self.assertIn("screenshot", tools["tools"])
        schema_names = [tool["name"] for tool in schemas["tools"]]
        self.assertIn("run_script", schema_names)
        self.assertIn("request_schema", schemas["tools"][0])
        example_names = [example["name"] for example in examples["examples"]]
        self.assertIn("dry_run_tap", example_names)
        self.assertIn("guarded_real_tap", example_names)

    def test_tool_endpoint_runs_request_through_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            ready = create_ai_tool_server(AiToolServerConfig(port=0, artifact_root=root))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)):
                    response = _post_json(ready.url + "tool", {"tool": "tap", "args": {"x": 1, "y": 2, "label": "open menu"}})
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertEqual(response["tool"], "tap")
            self.assertTrue(response["result"]["dry_run"])
            self.assertTrue((root / "agent" / "ai-bridge.jsonl").exists())

    def test_real_input_still_requires_explicit_server_policy(self):
        ready = create_ai_tool_server(AiToolServerConfig(port=0, allow_device_input=False))
        thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
        thread.start()
        try:
            response = _post_json(ready.url + "api/tool", {"tool": "tap", "args": {"x": 1, "y": 2, "execute": True}})
        finally:
            ready.server.shutdown()
            ready.server.server_close()
            thread.join(timeout=2)

        self.assertFalse(response["ok"])
        self.assertTrue(response["blocked"])
        self.assertIn("Real device input", response["messages"][0])

    def test_real_input_requires_device_input_code_when_server_configures_one(self):
        ready = create_ai_tool_server(AiToolServerConfig(port=0, allow_device_input=True, device_input_code="RUN-123"))
        thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
        thread.start()
        try:
            health = _get_json(ready.url + "health")
            missing = _post_json(ready.url + "tool", {"tool": "tap", "args": {"x": 1, "y": 2, "execute": True}})
            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0)):
                ok = _post_json(
                    ready.url + "tool",
                    {"tool": "tap", "args": {"x": 1, "y": 2, "execute": True, "device_input_code": "RUN-123"}},
                )
        finally:
            ready.server.shutdown()
            ready.server.server_close()
            thread.join(timeout=2)

        self.assertTrue(health["device_input"]["allowed"])
        self.assertTrue(health["device_input"]["code_required"])
        self.assertFalse(missing["ok"])
        self.assertTrue(missing["blocked"])
        self.assertTrue(ok["ok"])


def _get_json(url: str) -> dict:
    return json.loads(request.urlopen(url, timeout=2).read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(request.urlopen(req, timeout=2).read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
