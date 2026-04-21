from pathlib import Path
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.click_map import capture_click_map, write_click_map
from png_helpers import write_rgba_png


class ClickMapTest(unittest.TestCase):
    def test_write_click_map_embeds_screenshot_and_outputs_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            report = write_click_map(screenshot, html)

            self.assertEqual(report.screenshot_path, screenshot)
            self.assertEqual(report.html_path, html)
            content = html.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", content)
            self.assertIn("Recorder Commands", content)
            self.assertIn("Complete YAML Script", content)
            self.assertIn("Download Script", content)
            self.assertIn("Capture Latest", content)
            self.assertIn("steps:\\n", content)
            self.assertIn("tap ${step.x} ${step.y}", content)

    def test_write_click_map_uses_script_out_as_download_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            script = tmp_path / "my-daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            report = write_click_map(screenshot, html, script_path=script)

            self.assertEqual(report.script_path, script)
            self.assertIn('const scriptFilename = "my-daily.yml"', html.read_text(encoding="utf-8"))

    def test_capture_click_map_captures_before_writing_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"

            def fake_screenshot(out, adb_path=None, serial=None):
                write_rgba_png(Path(out), 1, 1, [(0, 0, 0, 255)])
                return AdbResult(command=["adb", "screencap"], returncode=0)

            with mock.patch("autoplay.api.screenshot", side_effect=fake_screenshot) as screenshot_api:
                report = capture_click_map(screenshot, html, script_path=tmp_path / "daily.yml", adb_path="adb", serial="device")

            screenshot_api.assert_called_once_with(screenshot, adb_path="adb", serial="device")
            self.assertTrue(report.screenshot_path.exists())
            self.assertTrue(report.html_path.exists())
            self.assertEqual(report.script_path, tmp_path / "daily.yml")

    def test_capture_click_map_does_not_write_html_when_screenshot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"

            with mock.patch("autoplay.api.screenshot", return_value=AdbResult(command=["adb"], returncode=1, stderr="boom")):
                report = capture_click_map(screenshot, html)

            self.assertEqual(report.screenshot_result.returncode, 1)
            self.assertFalse(html.exists())


if __name__ == "__main__":
    unittest.main()
