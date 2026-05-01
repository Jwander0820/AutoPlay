from pathlib import Path
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.click_map import capture_click_map, render_builder_html, write_click_map
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
            self.assertIn("錄製工作台", content)
            self.assertIn("Recorder 指令", content)
            self.assertIn("完整 YAML 腳本", content)
            self.assertIn("下載腳本", content)
            self.assertIn("擷取最新畫面", content)
            self.assertIn("測試腳本", content)
            self.assertIn("真實測試", content)
            self.assertIn("復原上一筆", content)
            self.assertIn("互動工具", content)
            self.assertIn("點擊工具：在畫面點一下就會新增 tap。", content)
            self.assertIn("滑動工具：直接在畫面上拖出起點與終點", content)
            self.assertIn("自動估算", content)
            self.assertIn("auto_wait", content)
            self.assertIn("stable_seconds", content)
            self.assertIn("const stepCaptureUrl = null", content)
            self.assertIn("deviceStepCapture", content)
            self.assertIn("手勢校準", content)
            self.assertIn("const calibration = {}", content)
            self.assertIn("readScrollDistance", content)
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

    def test_render_builder_html_can_show_calibration_guide_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            screenshot = Path(tmp) / "screen.png"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            html = render_builder_html(
                screenshot,
                screenshot.read_bytes(),
                Path(tmp) / "scripts" / "daily.yml",
                calibration_guide_command="py -m autoplay calibration guide --serial emulator-5554",
            )

            self.assertIn("校準指令", html)
            self.assertIn('id="copyCalibrationGuide"', html)
            self.assertIn("已複製校準指令", html)
            self.assertIn("calibration guide --serial emulator-5554", html)

    def test_render_builder_html_nudges_checkpoint_after_device_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            screenshot = Path(tmp) / "screen.png"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            html = render_builder_html(
                screenshot,
                screenshot.read_bytes(),
                Path(tmp) / "scripts" / "daily.yml",
                template_url="/api/template",
                step_capture_url="/api/device-step-capture",
            )

            self.assertIn("checkpointHintForCapture", html)
            self.assertIn('id="nextAction"', html)
            self.assertIn('id="nextActionDismiss"', html)
            self.assertIn("建議接著框選穩定 UI 區塊", html)
            self.assertIn("建立畫面驗證", html)
            self.assertIn("showNextAction", html)
            self.assertIn("已略過這次 checkpoint 提示", html)
            self.assertIn("setInteractionTool('crop'", html)

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
