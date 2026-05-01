from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib import request
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.image_match import read_png
from autoplay.calibration import load_calibration_for_serial
from autoplay.recorder_server import RecorderServerConfig, _calibration_guide_command, _calibration_ui_dict, _template_quality_messages, create_recorder_server
from png_helpers import write_rgba_png


class RecorderServerTest(unittest.TestCase):
    def test_calibration_guide_command_uses_current_serial_and_paths(self):
        config = RecorderServerConfig(
            script_path=Path("/tmp/project/scripts/daily.yml"),
            screenshot_path=Path("/tmp/project/artifacts/manual/start screen.png"),
            serial="emulator-5554",
        )

        command = _calibration_guide_command(config)

        self.assertIn("calibration guide --serial emulator-5554", command)
        self.assertIn("--from-screenshot '/tmp/project/artifacts/manual/start screen.png'", command)
        self.assertIn("--artifact-root /tmp/project/artifacts", command)

    def test_calibration_ui_dict_warns_when_screenshot_size_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 4, 3, [(255, 0, 0, 255)] * 12)
            calibration = tmp_path / "artifacts" / "calibration" / "bluestacks-emulator-5554.json"
            calibration.parent.mkdir(parents=True)
            calibration.write_text(
                json.dumps(
                    {
                        "serial": "emulator-5554",
                        "screen_width": 1200,
                        "screen_height": 2000,
                        "scroll_vertical_distance": 820,
                        "scroll_horizontal_distance": 560,
                    }
                ),
                encoding="utf-8",
            )

            data = _calibration_ui_dict(load_calibration_for_serial("emulator-5554", artifact_root=tmp_path / "artifacts"), screenshot)

            self.assertEqual(data["current_screen_width"], 4)
            self.assertEqual(data["current_screen_height"], 3)
            self.assertIn("Current screenshot is 4x3", data["warnings"][0])

    def test_template_quality_messages_warn_for_fragile_crops(self):
        messages = _template_quality_messages(4, 6, 100, 100, 0.85)

        self.assertIn("very small crop", " ".join(messages))
        self.assertIn("low threshold", " ".join(messages))

    def test_template_quality_messages_warn_for_large_crops(self):
        messages = _template_quality_messages(60, 60, 100, 100, 0.95)

        self.assertIn("large crop", " ".join(messages))

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

    def test_served_builder_shows_calibration_guide_command_for_serial(self):
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

            self.assertIn("calibration guide --serial emulator-5554", html)
            self.assertIn(f"--from-screenshot {screenshot.as_posix()}", html)
            self.assertIn(f"--artifact-root {(tmp_path / 'artifacts').as_posix()}", html)

    def test_served_builder_includes_device_step_capture_endpoint_when_enabled(self):
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
            try:
                html = request.urlopen(ready.url, timeout=2).read().decode("utf-8")
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertIn('const stepCaptureUrl = "/api/device-step-capture"', html)

    def test_served_builder_reflects_serial_calibration_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            calibration = tmp_path / "artifacts" / "calibration" / "bluestacks-emulator-5554.json"
            calibration.parent.mkdir(parents=True)
            calibration.write_text(
                json.dumps(
                    {
                        "serial": "emulator-5554",
                        "screen_width": 1200,
                        "screen_height": 2000,
                        "scroll_vertical_distance": 820,
                        "scroll_horizontal_distance": 560,
                        "default_swipe_duration_ms": 450,
                        "default_drag_duration_ms": 800,
                    }
                ),
                encoding="utf-8",
            )
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(
                self,
                RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0, serial="emulator-5554"),
            )
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                html = request.urlopen(ready.url, timeout=2).read().decode("utf-8")
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertIn('"loaded": true', html)
            self.assertIn('"screen_width": 1200', html)
            self.assertIn('"scroll_vertical_distance": 820', html)

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

    def test_device_step_capture_executes_swipe_and_returns_next_screenshot(self):
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
                write_rgba_png(Path(out), 1, 1, [(0, 0, 255, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            try:
                payload = json.dumps(
                    {
                        "step": {
                            "type": "swipe",
                            "x1": 10,
                            "y1": 20,
                            "x2": 30,
                            "y2": 40,
                            "duration_ms": 500,
                            "label": "open panel",
                        },
                        "wait_seconds": 0,
                    }
                ).encode("utf-8")
                capture_request = request.Request(
                    ready.url + "api/device-step-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with (
                    mock.patch("autoplay.recorder_server.api.swipe", return_value=AdbResult(command=["adb", "swipe"], returncode=0)) as swipe,
                    mock.patch("autoplay.recorder_server.api.screenshot", side_effect=fake_screenshot),
                ):
                    response = json.loads(request.urlopen(capture_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            swipe.assert_called_once_with(10, 20, 30, 40, duration_ms=500, adb_path=None, serial=None, execute=True)
            self.assertTrue(response["ok"])
            self.assertEqual([step["type"] for step in response["steps"]], ["swipe", "screenshot"])

    def test_device_step_capture_scroll_uses_calibrated_screen_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            calibration = tmp_path / "artifacts" / "calibration" / "bluestacks-emulator-5554.json"
            calibration.parent.mkdir(parents=True)
            calibration.write_text(
                json.dumps(
                    {
                        "serial": "emulator-5554",
                        "screen_width": 1200,
                        "screen_height": 2000,
                        "scroll_vertical_distance": 820,
                        "scroll_horizontal_distance": 560,
                    }
                ),
                encoding="utf-8",
            )
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(
                self,
                RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0, allow_device_input=True, serial="emulator-5554"),
            )
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()

            def fake_screenshot(out, adb_path=None, serial=None):
                write_rgba_png(Path(out), 1, 1, [(0, 0, 255, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            try:
                payload = json.dumps(
                    {
                        "step": {"type": "scroll", "direction": "down", "duration_ms": 400, "label": "scroll list"},
                        "wait_seconds": 0,
                    }
                ).encode("utf-8")
                capture_request = request.Request(
                    ready.url + "api/device-step-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with (
                    mock.patch("autoplay.recorder_server.api.scroll", return_value=AdbResult(command=["adb", "scroll"], returncode=0)) as scroll,
                    mock.patch("autoplay.recorder_server.api.screenshot", side_effect=fake_screenshot),
                ):
                    response = json.loads(request.urlopen(capture_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            scroll.assert_called_once_with(
                "down",
                distance=820,
                duration_ms=400,
                adb_path=None,
                serial="emulator-5554",
                execute=True,
                screen_width=1200,
                screen_height=2000,
            )
            self.assertTrue(response["ok"])
            self.assertEqual(response["steps"][0]["type"], "scroll")

    def test_device_step_capture_rejects_unsupported_step_type(self):
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
            try:
                payload = json.dumps({"step": {"type": "pinch"}, "wait_seconds": 0}).encode("utf-8")
                capture_request = request.Request(
                    ready.url + "api/device-step-capture",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(Exception):
                    request.urlopen(capture_request, timeout=2)
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

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

    def test_template_endpoint_crops_png_and_returns_checkpoint_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "artifacts" / "manual" / "screen.png"
            template = tmp_path / "artifacts" / "templates" / "button.png"
            script = tmp_path / "scripts" / "daily.yml"
            write_rgba_png(
                screenshot,
                3,
                2,
                [
                    (255, 0, 0, 255),
                    (0, 255, 0, 255),
                    (0, 0, 255, 255),
                    (255, 255, 255, 255),
                    (255, 0, 0, 255),
                    (0, 255, 0, 255),
                ],
            )
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps(
                    {
                        "source": screenshot.as_posix(),
                        "template": template.as_posix(),
                        "x": 1,
                        "y": 0,
                        "width": 2,
                        "height": 2,
                        "threshold": 0.9,
                    }
                ).encode("utf-8")
                template_request = request.Request(
                    ready.url + "api/template",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = json.loads(request.urlopen(template_request, timeout=2).read().decode("utf-8"))
            finally:
                ready.server.shutdown()
                ready.server.server_close()
                thread.join(timeout=2)

            self.assertTrue(response["ok"])
            self.assertEqual(response["template_path"], template.as_posix())
            self.assertEqual(response["steps"][0]["type"], "checkpoint_match")
            self.assertEqual(response["steps"][0]["threshold"], 0.9)
            self.assertTrue(response["match_preview"]["matched"])
            self.assertEqual(response["match_preview"]["score"], 1.0)
            self.assertIn("Checkpoint preview: matched=true", " ".join(response["messages"]))
            cropped = read_png(template)
            self.assertEqual((cropped.width, cropped.height), (2, 2))
            self.assertEqual(cropped.pixel(0, 0), (0, 255, 0, 255))

    def test_template_endpoint_rejects_out_of_bounds_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "artifacts" / "manual" / "screen.png"
            script = tmp_path / "scripts" / "daily.yml"
            template = tmp_path / "artifacts" / "templates" / "button.png"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])
            ready = _create_or_skip(self, RecorderServerConfig(script_path=script, screenshot_path=screenshot, port=0))
            thread = threading.Thread(target=ready.server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = json.dumps(
                    {
                        "source": screenshot.as_posix(),
                        "template": template.as_posix(),
                        "x": 0,
                        "y": 0,
                        "width": 2,
                        "height": 1,
                    }
                ).encode("utf-8")
                template_request = request.Request(
                    ready.url + "api/template",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(Exception):
                    request.urlopen(template_request, timeout=2)
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
