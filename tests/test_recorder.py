from pathlib import Path
from io import StringIO
import tempfile
import unittest
from unittest import mock

import yaml

from autoplay.recorder import append_step_to_script, parse_record_command, record_script
from autoplay.script import BackStep, CheckpointMatchStep, DragStep, ScriptError, ScrollStep, SwipeStep, load_script, ScreenshotStep, TapStep, WaitStep


class RecorderTest(unittest.TestCase):
    def test_parse_supported_commands(self):
        self.assertEqual(
            parse_record_command("screenshot artifacts/manual/start.png"),
            {"type": "screenshot", "out": "artifacts/manual/start.png"},
        )
        self.assertEqual(parse_record_command("wait 1.5"), {"type": "wait", "seconds": 1.5})
        self.assertEqual(
            parse_record_command("tap 10 20 open daily panel"),
            {"type": "tap", "x": 10, "y": 20, "label": "open daily panel"},
        )
        self.assertEqual(
            parse_record_command("checkpoint_exists artifacts/manual/start.png"),
            {"type": "checkpoint_exists", "path": "artifacts/manual/start.png"},
        )
        self.assertEqual(
            parse_record_command("checkpoint_match artifacts/manual/start.png artifacts/templates/button.png"),
            {"type": "checkpoint_match", "source": "artifacts/manual/start.png", "template": "artifacts/templates/button.png"},
        )
        self.assertEqual(
            parse_record_command("checkpoint_match artifacts/manual/start.png artifacts/templates/button.png 0.9 8 10 20 30 40"),
            {
                "type": "checkpoint_match",
                "source": "artifacts/manual/start.png",
                "template": "artifacts/templates/button.png",
                "threshold": 0.9,
                "tolerance": 8,
                "region": [10, 20, 30, 40],
            },
        )
        self.assertEqual(
            parse_record_command("swipe 10 20 30 40 500 scroll list"),
            {"type": "swipe", "x1": 10, "y1": 20, "x2": 30, "y2": 40, "duration_ms": 500, "label": "scroll list"},
        )
        self.assertEqual(
            parse_record_command("drag 10 20 30 40 900 move slider"),
            {"type": "drag", "x1": 10, "y1": 20, "x2": 30, "y2": 40, "duration_ms": 900, "label": "move slider"},
        )
        self.assertEqual(
            parse_record_command("scroll down 700 400 quest list"),
            {"type": "scroll", "direction": "down", "distance": 700, "duration_ms": 400, "label": "quest list"},
        )
        self.assertEqual(parse_record_command("back close panel"), {"type": "back", "label": "close panel"})

    def test_parse_rejects_unknown_or_unsafe_tap(self):
        with self.assertRaisesRegex(ScriptError, "Unknown"):
            parse_record_command("purchase item")
        with self.assertRaisesRegex(ScriptError, "tap usage"):
            parse_record_command("tap 10 20")
        with self.assertRaisesRegex(ScriptError, "non-negative"):
            parse_record_command("tap -1 20 label")
        with self.assertRaisesRegex(ScriptError, "threshold"):
            parse_record_command("checkpoint_match source.png template.png 1.5")
        with self.assertRaisesRegex(ScriptError, "tolerance"):
            parse_record_command("checkpoint_match source.png template.png 0.95 300")
        with self.assertRaisesRegex(ScriptError, "region"):
            parse_record_command("checkpoint_match source.png template.png 0.95 0 0 0 0 1")

    def test_record_script_appends_steps_and_validates_after_each_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            input_stream = StringIO(
                "\n".join(
                    [
                        "screenshot artifacts/manual/start.png",
                        "checkpoint_exists artifacts/manual/start.png",
                        "tap 10 20 open panel",
                        "wait 0",
                        "done",
                    ]
                )
                + "\n"
            )
            output_stream = StringIO()

            report = record_script(script_path, input_stream=input_stream, output_stream=output_stream)

            self.assertEqual(report.appended_steps, 4)
            script = load_script(script_path)
            self.assertIsInstance(script.steps[0], ScreenshotStep)
            self.assertIsInstance(script.steps[2], TapStep)
            self.assertIsInstance(script.steps[3], WaitStep)
            self.assertIn("OK: script passed validation.", output_stream.getvalue())

    def test_record_script_appends_gesture_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            input_stream = StringIO(
                "\n".join(
                    [
                        "swipe 10 20 30 40 500 scroll list",
                        "drag 10 20 30 40 900 move slider",
                        "scroll down 700 400 quest list",
                        "back close panel",
                        "done",
                    ]
                )
                + "\n"
            )

            record_script(script_path, input_stream=input_stream, output_stream=StringIO())

            script = load_script(script_path)
            self.assertIsInstance(script.steps[0], SwipeStep)
            self.assertIsInstance(script.steps[1], DragStep)
            self.assertIsInstance(script.steps[2], ScrollStep)
            self.assertIsInstance(script.steps[3], BackStep)

    def test_record_script_appends_checkpoint_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            input_stream = StringIO(
                "checkpoint_match artifacts/manual/start.png artifacts/templates/button.png 0.9 8 10 20 30 40\ndone\n"
            )

            record_script(script_path, input_stream=input_stream, output_stream=StringIO())

            script = load_script(script_path)
            step = script.steps[0]
            self.assertIsInstance(step, CheckpointMatchStep)
            self.assertEqual(step.threshold, 0.9)
            self.assertEqual(step.tolerance, 8)
            self.assertEqual((step.region.x, step.region.y, step.region.width, step.region.height), (10, 20, 30, 40))

    def test_record_script_preserves_existing_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
profile:
  serial: emulator-5554
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )
            input_stream = StringIO("wait 1\ndone\n")

            record_script(script_path, input_stream=input_stream, output_stream=StringIO())

            data = yaml.safe_load(script_path.read_text(encoding="utf-8"))
            self.assertEqual(data["profile"]["serial"], "emulator-5554")
            self.assertEqual(len(data["steps"]), 2)

    def test_record_script_never_sends_taps(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            with mock.patch("autoplay.api.tap") as tap:
                record_script(script_path, input_stream=StringIO("tap 10 20 safe label\ndone\n"), output_stream=StringIO())

            tap.assert_not_called()

    def test_append_step_to_script_preserves_existing_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
profile:
  serial: emulator-5554
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            append_step_to_script(script_path, {"type": "tap", "x": 1, "y": 2, "label": "live click 1"})

            data = yaml.safe_load(script_path.read_text(encoding="utf-8"))
            self.assertEqual(data["profile"]["serial"], "emulator-5554")
            self.assertEqual(data["steps"][-1]["type"], "tap")


if __name__ == "__main__":
    unittest.main()
