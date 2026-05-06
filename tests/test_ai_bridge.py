from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.ai_bridge import AiBridge, AiBridgeConfig
from autoplay.local_config import LocalConfig


class AiBridgeTest(unittest.TestCase):
    def test_tap_defaults_to_dry_run_and_returns_json_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            bridge = AiBridge(AiBridgeConfig(artifact_root=root, audit_path=root / "agent" / "ai.jsonl"))

            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "shell", "input", "tap", "10", "20"], returncode=0, dry_run=True)):
                response = bridge.handle({"tool": "tap", "args": {"x": 10, "y": 20, "label": "open menu"}})

            self.assertTrue(response["ok"])
            self.assertEqual(response["tool"], "tap")
            self.assertTrue(response["result"]["dry_run"])
            self.assertEqual(response["result"]["command"], ["adb", "shell", "input", "tap", "10", "20"])
            self.assertEqual(response["steps_remaining"], 19)

    def test_real_input_is_blocked_without_bridge_policy_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            bridge = AiBridge(AiBridgeConfig(artifact_root=root, audit_path=root / "agent" / "ai.jsonl"))

            response = bridge.handle({"tool": "tap", "args": {"x": 10, "y": 20, "label": "open menu", "execute": True}})

            self.assertFalse(response["ok"])
            self.assertTrue(response["blocked"])
            self.assertIn("Real device input", response["messages"][0])

    def test_real_input_requires_device_input_code_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            bridge = AiBridge(
                AiBridgeConfig(
                    artifact_root=root,
                    audit_path=root / "agent" / "ai.jsonl",
                    allow_device_input=True,
                    device_input_code="RUN-123",
                )
            )

            missing = bridge.handle({"tool": "tap", "args": {"x": 10, "y": 20, "label": "open menu", "execute": True}})
            wrong = bridge.handle(
                {"tool": "tap", "args": {"x": 10, "y": 20, "label": "open menu", "execute": True, "device_input_code": "BAD"}}
            )
            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0)) as tap:
                ok = bridge.handle(
                    {"tool": "tap", "args": {"x": 10, "y": 20, "label": "open menu", "execute": True, "device_input_code": "RUN-123"}}
                )

            self.assertFalse(missing["ok"])
            self.assertTrue(missing["blocked"])
            self.assertFalse(wrong["ok"])
            self.assertTrue(wrong["blocked"])
            self.assertTrue(ok["ok"])
            tap.assert_called_once_with(10, 20, adb_path=None, serial=None, execute=True)

    def test_from_local_config_uses_private_runtime_adb_path_without_committed_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            local = LocalConfig(adb_path="C:/Emulator/adb.exe", serial="127.0.0.1:5555")
            bridge = AiBridge.from_local_config(local_config=local, artifact_root=root)

            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)) as tap:
                response = bridge.handle({"tool": "tap", "args": {"x": 1, "y": 2, "label": "open menu"}})

            self.assertTrue(response["ok"])
            tap.assert_called_once_with(1, 2, adb_path="C:/Emulator/adb.exe", serial="127.0.0.1:5555", execute=False)

    def test_unknown_tool_returns_error_response(self):
        bridge = AiBridge()

        response = bridge.handle({"tool": "missing_tool", "args": {}})

        self.assertFalse(response["ok"])
        self.assertEqual(response["tool"], "missing_tool")
        self.assertIn("Unknown AI tool", response["messages"][0])

    def test_draft_script_tool_writes_reviewable_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scripts"
            bridge = AiBridge(AiBridgeConfig(script_root=root, artifact_root=Path(tmp) / "artifacts"))
            script = root / "ai-draft.yml"

            response = bridge.handle(
                {
                    "tool": "draft_script",
                    "args": {"script": str(script), "steps": [{"type": "wait", "seconds": 0}]},
                }
            )

            self.assertTrue(response["ok"])
            self.assertEqual(response["tool"], "draft_script")
            self.assertEqual(response["result"]["step_count"], 1)
            self.assertTrue(script.exists())

    def test_writes_audit_under_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            audit = root / "agent" / "ai.jsonl"
            bridge = AiBridge(AiBridgeConfig(artifact_root=root, audit_path=audit))

            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)):
                bridge.handle({"tool": "tap", "args": {"x": 1, "y": 2, "label": "open menu"}})

            events = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["tool"], "tap")
            self.assertEqual(events[0]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
