from pathlib import Path
import tempfile
import unittest

from autoplay.script import load_script
from autoplay.validation import format_report, validate_script, validate_script_file
from png_helpers import write_rgba_png


class ValidationTest(unittest.TestCase):
    def test_valid_smoke_style_script_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            script_path.write_text(
                """
steps:
  - type: screenshot
    out: artifacts/screen.png
  - type: checkpoint_exists
    path: artifacts/screen.png
  - type: tap
    x: 10
    y: 20
    label: open mission panel
""",
                encoding="utf-8",
            )

            report = validate_script(load_script(script_path))

            self.assertTrue(report.ok)
            self.assertEqual(report.errors, [])

    def test_checkpoint_without_source_is_error(self):
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

            report = validate_script_file(script_path)

            self.assertFalse(report.ok)
            self.assertIn("neither created", report.errors[0].message)

    def test_tap_without_label_is_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: tap
    x: 10
    y: 20
""",
                encoding="utf-8",
            )

            report = validate_script_file(script_path)

            self.assertTrue(report.ok)
            self.assertEqual(len(report.warnings), 1)
            self.assertIn("no label", report.warnings[0].message)

    def test_format_report_for_clean_script(self):
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

            self.assertEqual(format_report(validate_script_file(script_path)), ["OK: script passed validation."])

    def test_checkpoint_match_accepts_earlier_screenshot_source_and_existing_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "templates" / "ok.png"
            write_rgba_png(template, 1, 1, [(255, 0, 0, 255)])
            script_path = tmp_path / "script.yml"
            script_path.write_text(
                """
steps:
  - type: screenshot
    out: artifacts/screen.png
  - type: checkpoint_match
    source: artifacts/screen.png
    template: templates/ok.png
""",
                encoding="utf-8",
            )

            report = validate_script_file(script_path)

            self.assertTrue(report.ok)
            self.assertEqual(report.errors, [])

    def test_checkpoint_match_requires_template_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: screenshot
    out: artifacts/screen.png
  - type: checkpoint_match
    source: artifacts/screen.png
    template: templates/missing.png
""",
                encoding="utf-8",
            )

            report = validate_script_file(script_path)

            self.assertFalse(report.ok)
            self.assertIn("template file does not exist", report.errors[0].message)


if __name__ == "__main__":
    unittest.main()
