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
                self.assertIn("Save Script", html)

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


def _create_or_skip(test_case: unittest.TestCase, config: RecorderServerConfig):
    try:
        return create_recorder_server(config)
    except PermissionError as exc:
        test_case.skipTest(f"localhost sockets are unavailable in this sandbox: {exc}")


if __name__ == "__main__":
    unittest.main()
