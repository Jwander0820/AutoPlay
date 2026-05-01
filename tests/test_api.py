from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from autoplay import api
from autoplay.adb import AdbResult
from autoplay.runner import RunnerError
from autoplay.script import ScriptError
from png_helpers import write_rgba_png


class ApiTest(unittest.TestCase):
    def test_tap_defaults_to_dry_run(self):
        with mock.patch("autoplay.api.resolve_adb_path", return_value="adb"):
            result = api.tap(10, 20)

        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.command, ["adb", "shell", "input", "tap", "10", "20"])

    def test_tap_execute_sends_command_through_adb_client(self):
        with (
            mock.patch("autoplay.api.resolve_adb_path", return_value="/custom/adb"),
            mock.patch("autoplay.api.AdbClient") as client_class,
        ):
            client = client_class.return_value
            client.tap.return_value = AdbResult(command=["adb", "tap"], returncode=0)

            result = api.tap(10, 20, adb_path="/custom/adb", serial="device-1", execute=True)

        client_class.assert_called_once_with(adb_path="/custom/adb", serial="device-1")
        client.tap.assert_called_once_with(10, 20, dry_run=False)
        self.assertTrue(result.ok)

    def test_tap_rejects_negative_coordinates(self):
        with self.assertRaisesRegex(ScriptError, "non-negative"):
            api.tap(-1, 20)

    def test_swipe_drag_scroll_back_default_to_dry_run(self):
        with mock.patch("autoplay.api.resolve_adb_path", return_value="adb"):
            swipe = api.swipe(10, 20, 30, 40, duration_ms=500)
            drag = api.drag(50, 60, 70, 80, duration_ms=900)
            scroll = api.scroll("down", distance=700, duration_ms=400)
            back = api.back()

        self.assertTrue(swipe.dry_run)
        self.assertEqual(swipe.command, ["adb", "shell", "input", "swipe", "10", "20", "30", "40", "500"])
        self.assertTrue(drag.dry_run)
        self.assertEqual(drag.command, ["adb", "shell", "input", "swipe", "50", "60", "70", "80", "900"])
        self.assertTrue(scroll.dry_run)
        self.assertEqual(scroll.command, ["adb", "shell", "input", "swipe", "540", "610", "540", "1310", "400"])
        self.assertTrue(back.dry_run)
        self.assertEqual(back.command, ["adb", "shell", "input", "keyevent", "BACK"])

    def test_gestures_reject_unbounded_parameters(self):
        with self.assertRaisesRegex(ScriptError, "non-negative"):
            api.swipe(-1, 0, 1, 1)
        with self.assertRaisesRegex(ScriptError, "duration_ms"):
            api.drag(0, 0, 1, 1, duration_ms=10)
        with self.assertRaisesRegex(ScriptError, "direction"):
            api.scroll("diagonal")
        with self.assertRaisesRegex(ScriptError, "distance"):
            api.scroll("down", distance=0)

    def test_scroll_accepts_calibrated_screen_size(self):
        with mock.patch("autoplay.api.resolve_adb_path", return_value="adb"):
            result = api.scroll("down", distance=800, duration_ms=400, screen_width=1200, screen_height=2000)

        self.assertEqual(result.command, ["adb", "shell", "input", "swipe", "600", "600", "600", "1400", "400"])

    def test_run_validates_before_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: checkpoint_exists
    path: missing.png
""",
                encoding="utf-8",
            )

            with mock.patch("autoplay.api.run_script_file") as run_script_file:
                with self.assertRaisesRegex(RunnerError, "Script validation failed"):
                    api.run(script_path)

        run_script_file.assert_not_called()

    def test_run_defaults_to_dry_run_taps_and_writes_report(self):
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

            report = api.run(script_path, report_out=report_path)

            self.assertTrue(report.dry_run_taps)
            written = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], "ok")

    def test_match_accepts_sequence_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 2, 1, [(0, 0, 0, 255), (255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(255, 0, 0, 255)])

            result = api.match(source, template, threshold=1.0, region=[1, 0, 1, 1])

            self.assertTrue(result.matched)
            self.assertEqual((result.x, result.y), (1, 0))

    def test_match_rejects_unbounded_parameters(self):
        with self.assertRaisesRegex(ScriptError, "threshold"):
            api.match("source.png", "template.png", threshold=1.1)
        with self.assertRaisesRegex(ScriptError, "tolerance"):
            api.match("source.png", "template.png", tolerance=256)
        with self.assertRaisesRegex(ScriptError, "region"):
            api.match("source.png", "template.png", region=[0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
