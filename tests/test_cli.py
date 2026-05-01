from pathlib import Path
import json
from io import StringIO
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.cli import main
from png_helpers import write_rgba_png


class CliTest(unittest.TestCase):
    def test_validate_returns_zero_for_valid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["validate", str(script_path)]), 0)

    def test_validate_returns_one_for_invalid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: checkpoint_exists
    path: artifacts/missing.png
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["validate", str(script_path)]), 1)

    def test_match_returns_zero_when_template_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["match", str(source), str(template), "--threshold", "1"]), 0)

    def test_match_returns_one_when_template_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(0, 0, 255, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["match", str(source), str(template), "--threshold", "1"]), 1)

    def test_run_writes_report_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            report_path = tmp_path / "report.json"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["run", str(script_path), "--report-out", str(report_path)]), 0)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["events"][0]["step_type"], "wait")

    def test_gesture_commands_default_to_dry_run(self):
        with mock.patch("builtins.print"):
            self.assertEqual(main(["swipe", "10", "20", "30", "40", "--duration-ms", "500"]), 0)
            self.assertEqual(main(["drag", "10", "20", "30", "40", "--duration-ms", "900"]), 0)
            self.assertEqual(main(["scroll", "down", "--distance", "700", "--duration-ms", "400"]), 0)
            self.assertEqual(main(["back"]), 0)

    def test_scroll_can_use_calibration_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            calibration = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
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

            stdout = StringIO()
            with mock.patch("sys.stdout", stdout):
                self.assertEqual(
                    main(["scroll", "down", "--calibrated", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]),
                    0,
                )

            output = stdout.getvalue()
            self.assertIn("shell input swipe 600 590 600 1410 400", output)
            self.assertIn("-s emulator-5554", output)

    def test_calibration_write_and_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"

            with mock.patch("builtins.print"):
                self.assertEqual(
                    main(
                        [
                            "calibration",
                            "write",
                            "--serial",
                            "emulator-5554",
                            "--artifact-root",
                            str(artifact_root),
                            "--screen-width",
                            "1200",
                            "--screen-height",
                            "2000",
                            "--scroll-vertical-distance",
                            "820",
                            "--scroll-horizontal-distance",
                            "560",
                        ]
                    ),
                    0,
                )

            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            self.assertTrue(path.exists())
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 1200)
            self.assertEqual(written["scroll_horizontal_distance"], 560)

            stdout = StringIO()
            with mock.patch("sys.stdout", stdout):
                self.assertEqual(main(["calibration", "show", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]), 0)

            output = stdout.getvalue()
            self.assertIn("Loaded: true", output)
            self.assertIn("screen: 1200x2000", output)

            json_stdout = StringIO()
            with mock.patch("sys.stdout", json_stdout):
                self.assertEqual(main(["calibration", "show", "--json", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]), 0)

            shown = json.loads(json_stdout.getvalue())
            self.assertTrue(shown["loaded"])
            self.assertEqual(shown["screen_width"], 1200)

    def test_calibration_write_rejects_bad_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("sys.stderr", new_callable=StringIO) as stderr:
                self.assertEqual(
                    main(["calibration", "write", "--artifact-root", tmp, "--screen-width", "0"]),
                    1,
                )

            self.assertIn("screen_width must be a positive integer", stderr.getvalue())

    def test_calibration_write_can_infer_screen_size_from_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / "artifacts"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 3, 2, [(255, 0, 0, 255)] * 6)

            with mock.patch("builtins.print"):
                self.assertEqual(
                    main(["calibration", "write", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--from-screenshot", str(screenshot)]),
                    0,
                )

            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 3)
            self.assertEqual(written["screen_height"], 2)

    def test_calibration_guide_saves_profile_and_notes_without_real_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / "artifacts"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 4, 3, [(255, 0, 0, 255)] * 12)
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe", "2", "1", "2", "2", "400"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("short\nok\n560\nok\nyes\ncalibrated on laptop\n")),
                mock.patch("sys.stdout", StringIO()),
            ):
                self.assertEqual(
                    main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--from-screenshot", str(screenshot)]),
                    0,
                )

            self.assertEqual(execute_flags, [False, False, False, False])
            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            note = artifact_root / "calibration" / "bluestacks-emulator-5554-notes.md"
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 4)
            self.assertEqual(written["screen_height"], 3)
            self.assertEqual(written["scroll_vertical_distance"], 780)
            self.assertEqual(written["scroll_horizontal_distance"], 560)
            self.assertIn("calibrated on laptop", note.read_text(encoding="utf-8"))

    def test_calibration_guide_requires_yes_prompt_for_real_scroll(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("yes\nok\n\nok\nyes\n\n")),
                mock.patch("sys.stdout", StringIO()),
            ):
                self.assertEqual(
                    main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--yes"]),
                    0,
                )

            self.assertEqual(execute_flags, [False, True, False])

    def test_calibration_guide_keeps_invalid_feedback_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("banana\nok\nok\nyes\n\n")),
                mock.patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                self.assertEqual(main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--max-rounds", "2"]), 0)

            self.assertEqual(execute_flags, [False, False, False])
            self.assertIn("Invalid feedback", stdout.getvalue())

    def test_calibration_guide_reports_missing_interactive_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch("sys.stdin", StringIO("")),
                mock.patch("sys.stdout", StringIO()),
                mock.patch("sys.stderr", new_callable=StringIO) as stderr,
            ):
                self.assertEqual(main(["calibration", "guide", "--artifact-root", tmp]), 1)

            self.assertIn("calibration guide requires interactive input", stderr.getvalue())

    def test_calibration_guide_rejects_invalid_max_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch("sys.stdout", StringIO()),
                mock.patch("sys.stderr", new_callable=StringIO) as stderr,
            ):
                self.assertEqual(main(["calibration", "guide", "--artifact-root", tmp, "--max-rounds", "0"]), 1)

            self.assertIn("--max-rounds must be a positive integer", stderr.getvalue())

    def test_record_appends_step_from_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"

            with mock.patch("sys.stdin", StringIO("wait 0\ndone\n")), mock.patch("sys.stdout", StringIO()):
                self.assertEqual(main(["record", str(script_path)]), 0)

            self.assertIn("type: wait", script_path.read_text(encoding="utf-8"))

    def test_agent_run_writes_report_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            artifact_root = tmp_path / "artifacts"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["agent-run", str(script_path), "--artifact-root", str(artifact_root)]), 0)

            self.assertTrue((artifact_root / "reports" / "script-agent-dry-run.json").exists())
            self.assertTrue((artifact_root / "agent" / "script-audit.jsonl").exists())

    def test_screenshot_multiple_devices_prints_serial_hint(self):
        result = AdbResult(command=["adb", "exec-out", "screencap", "-p"], returncode=1, stderr="error: more than one device/emulator")
        doctor_report = mock.Mock(lines=["Connected devices: emulator-5554, 127.0.0.1:5555"])

        with (
            mock.patch("autoplay.cli.api.screenshot", return_value=result),
            mock.patch("autoplay.cli.api.doctor", return_value=doctor_report),
            mock.patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            self.assertEqual(main(["screenshot", "--out", "artifacts/manual/screen.png"]), 1)

        output = stderr.getvalue()
        self.assertIn("more than one device/emulator", output)
        self.assertIn("--serial emulator-5554", output)
        self.assertIn("--serial 127.0.0.1:5555", output)

    def test_click_map_writes_html_from_existing_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["click-map", str(screenshot), "--out", str(html)]), 0)

            html_text = html.read_text(encoding="utf-8")
            self.assertIn("AutoPlay 錄製工作台", html_text)
            self.assertIn("互動工具", html_text)
            self.assertIn("快速補步驟與手勢微調", html_text)

    def test_click_map_uses_script_out_download_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            script = tmp_path / "my-daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["click-map", str(screenshot), "--out", str(html), "--script-out", str(script)]), 0)

            self.assertIn('const scriptFilename = "my-daily.yml"', html.read_text(encoding="utf-8"))

    def test_record_ui_starts_and_stops_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "daily.yml"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("autoplay.cli.create_recorder_server") as create_server, mock.patch("builtins.print") as printer:
                server = create_server.return_value.server
                server.serve_forever.side_effect = KeyboardInterrupt()
                self.assertEqual(main(["record-ui", str(script), "--screenshot", str(screenshot), "--port", "0", "--allow-device-input"]), 0)

            create_server.assert_called_once()
            config = create_server.call_args.args[0]
            self.assertTrue(config.allow_device_input)
            server.server_close.assert_called_once()
            printed = "\n".join(str(call.args[0]) for call in printer.call_args_list)
            self.assertIn("Calibration: defaults", printed)

    def test_record_clicks_delegates_to_live_click_recorder(self):
        with mock.patch("autoplay.cli.run_windows_live_click_recorder", return_value=[]) as recorder, mock.patch("builtins.print"):
            self.assertEqual(main(["record-clicks", "scripts/daily.yml", "--screenshot", "artifacts/manual/start.png", "--max-clicks", "1"]), 0)

        recorder.assert_called_once_with(
            "scripts/daily.yml",
            screenshot_path="artifacts/manual/start.png",
            window_title="BlueStacks",
            label_prefix="live click",
            max_clicks=1,
        )


if __name__ == "__main__":
    unittest.main()
