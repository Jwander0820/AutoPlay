from pathlib import Path
import json
from io import StringIO
import tempfile
import unittest
from unittest import mock

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

    def test_click_map_writes_html_from_existing_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["click-map", str(screenshot), "--out", str(html)]), 0)

            self.assertIn("AutoPlay Script Builder", html.read_text(encoding="utf-8"))

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

            with mock.patch("autoplay.cli.create_recorder_server") as create_server, mock.patch("builtins.print"):
                server = create_server.return_value.server
                server.serve_forever.side_effect = KeyboardInterrupt()
                self.assertEqual(main(["record-ui", str(script), "--screenshot", str(screenshot), "--port", "0", "--allow-device-input"]), 0)

            create_server.assert_called_once()
            config = create_server.call_args.args[0]
            self.assertTrue(config.allow_device_input)
            server.server_close.assert_called_once()

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
