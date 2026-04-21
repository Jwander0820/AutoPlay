from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib import request
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.recorder_server import RecorderServerConfig, create_recorder_server
from png_helpers import write_rgba_png


class RecorderServerTest(unittest.TestCase):
    def test_serves_builder_and_saves_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                html = request.urlopen(ready.url, timeout=2).read().decode("utf-8")
                self.assertIn("儲存並驗證", html)

                payload = json.dumps({"yaml": "steps:\n  - type: wait\n    seconds: 0\n"}).encode("utf-8")
                save_request = request.Request(
                    ready.url + "api/script",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = json.loads(request.urlopen(save_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertEqual(response["status"], "saved")
            self.assertIn("OK: script passed validation.", response["messages"])
            self.assertIn("type: wait", script.read_text(encoding="utf-8"))

    def test_served_builder_embeds_target_serial_in_generated_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0, serial="emulator-5554"))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                html = request.urlopen(ready.url, timeout=2).read().decode("utf-8")
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertIn('"serial": "emulator-5554"', html)
            self.assertIn("profileToYaml", html)

    def test_save_reports_validation_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps({"yaml": "steps:\n  - type: checkpoint_exists\n    path: missing.png\n"}).encode("utf-8")
                save_request = request.Request(
                    ready.url + "api/script",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = json.loads(request.urlopen(save_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertFalse(response["ok"])
            self.assertIn("ERROR:", response["messages"][0])

    def test_capture_latest_returns_new_screenshot_and_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()

            def fake_screenshot(out, adb_path=None, serial=None):
                write_rgba_png(Path(out), 1, 1, [(0, 0, 255, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            try:
                with mock.patch("autoplay.recorder_server.api.screenshot", side_effect=fake_screenshot):
                    save_request = request.Request(
                        ready.url + "api/capture",
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    response = json.loads(request.urlopen(save_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertTrue(response["screenshot_path"].endswith("screen-001.png"))
            self.assertEqual(response["steps"][0]["type"], "screenshot")
            self.assertIn("data:image/png;base64,", response["image_data_url"])

    def test_tap_capture_requires_device_input_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps({"x": 1, "y": 2, "label": "open", "wait_seconds": 0}).encode("utf-8")
                save_request = request.Request(
                    ready.url + "api/tap-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(Exception):
                    request.urlopen(save_request, timeout=2)
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

    def test_tap_capture_executes_tap_and_returns_next_screenshot_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(
                self,
                RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0, allow_device_input=True),
            )
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()

            def fake_screenshot(out, adb_path=None, serial=None):
                write_rgba_png(Path(out), 1, 1, [(0, 255, 0, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            try:
                payload = json.dumps({"x": 1, "y": 2, "label": "open", "wait_seconds": 0}).encode("utf-8")
                save_request = request.Request(
                    ready.url + "api/tap-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with (
                    mock.patch("autoplay.recorder_server.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0)) as tap,
                    mock.patch("autoplay.recorder_server.api.screenshot", side_effect=fake_screenshot),
                ):
                    response = json.loads(request.urlopen(save_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            tap.assert_called_once_with(1, 2, adb_path=None, serial=None, execute=True)
            self.assertTrue(response["ok"])
            self.assertEqual([step["type"] for step in response["steps"]], ["tap", "screenshot"])

    def test_tap_capture_auto_wait_until_screen_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(
                self,
                RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0, allow_device_input=True),
            )
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()

            def fake_screenshot(out, adb_path=None, serial=None):
                write_rgba_png(Path(out), 1, 1, [(0, 255, 0, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            try:
                payload = json.dumps(
                    {
                        "x": 1,
                        "y": 2,
                        "label": "open",
                        "auto_wait": True,
                        "min_wait_seconds": 0,
                        "max_wait_seconds": 1,
                        "poll_seconds": 0,
                        "stable_seconds": 0,
                    }
                ).encode("utf-8")
                save_request = request.Request(
                    ready.url + "api/tap-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with (
                    mock.patch("autoplay.recorder_server.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0)),
                    mock.patch("autoplay.recorder_server.api.screenshot", side_effect=fake_screenshot) as screenshot_api,
                ):
                    response = json.loads(request.urlopen(save_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertTrue(response["auto_wait"])
            self.assertIn("wait_seconds", response)
            self.assertEqual(response["steps"][0]["type"], "tap")
            self.assertEqual(response["steps"][-1]["type"], "screenshot")
            screenshot_api.assert_called_once()

    def test_run_endpoint_saves_current_yaml_and_runs_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps({"yaml": "steps:\n  - type: wait\n    seconds: 0\n", "execute_taps": False}).encode("utf-8")
                run_request = request.Request(
                    ready.url + "api/run",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = json.loads(request.urlopen(run_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertTrue(response["dry_run_taps"])
            self.assertTrue(response["report_path"].endswith("daily-agent-dry-run.json"))
            self.assertTrue(response["audit_path"].endswith("daily-audit.jsonl"))
            self.assertIn("type: wait", script.read_text(encoding="utf-8"))

    def test_run_endpoint_blocks_real_taps_without_device_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps(
                    {
                        "yaml": "steps:\n  - type: tap\n    x: 1\n    y: 2\n    label: open\n",
                        "execute_taps": True,
                    }
                ).encode("utf-8")
                run_request = request.Request(
                    ready.url + "api/run",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(Exception):
                    request.urlopen(run_request, timeout=2)
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)


def _create_or_skip(test_case: unittest.TestCase, config: RecorderServerConfig):
    try:
        return create_recorder_server(config)
    except PermissionError as exc:
        test_case.skipTest(f"localhost sockets are unavailable in this sandbox: {exc}")


if __name__ == "__main__":
    unittest.main()
