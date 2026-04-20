from pathlib import Path
import json
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


if __name__ == "__main__":
    unittest.main()
