from pathlib import Path
import tempfile
import unittest

from autoplay.script import BackStep, CheckpointExistsStep, CheckpointMatchStep, DragStep, ScreenshotStep, ScriptError, ScrollStep, SwipeStep, TapStep, WaitStep, load_script


class ScriptTest(unittest.TestCase):
    def test_load_valid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            script_path.write_text(
                """
profile:
  adb_path: /tmp/adb
  serial: emulator-5554
steps:
  - type: wait
    seconds: 0.1
  - type: tap
    x: 10
    y: 20
  - type: screenshot
    out: artifacts/screen.png
  - type: checkpoint_exists
    path: artifacts/screen.png
""",
                encoding="utf-8",
            )

            script = load_script(script_path)

            self.assertEqual(script.profile.adb_path, "/tmp/adb")
            self.assertEqual(script.profile.serial, "emulator-5554")
            self.assertIsInstance(script.steps[0], WaitStep)
            self.assertIsInstance(script.steps[1], TapStep)
            self.assertIsInstance(script.steps[2], ScreenshotStep)
            self.assertEqual(script.steps[2].out, tmp_path / "artifacts/screen.png")
            self.assertIsInstance(script.steps[3], CheckpointExistsStep)

    def test_unknown_step_type_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: dance
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ScriptError, "Unknown step type"):
                load_script(script_path)

    def test_empty_steps_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text("steps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(ScriptError, "at least one step"):
                load_script(script_path)

    def test_negative_tap_coordinate_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: tap
    x: -1
    y: 20
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ScriptError, "non-negative"):
                load_script(script_path)

    def test_checkpoint_match_parses_defaults_and_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            script_path.write_text(
                """
steps:
  - type: checkpoint_match
    source: artifacts/screen.png
    template: templates/ok.png
    region: [10, 20, 30, 40]
""",
                encoding="utf-8",
            )

            script = load_script(script_path)
            step = script.steps[0]

            self.assertIsInstance(step, CheckpointMatchStep)
            self.assertEqual(step.source, tmp_path / "artifacts/screen.png")
            self.assertEqual(step.template, tmp_path / "templates/ok.png")
            self.assertEqual(step.threshold, 0.95)
            self.assertEqual(step.tolerance, 0)
            self.assertEqual((step.region.x, step.region.y, step.region.width, step.region.height), (10, 20, 30, 40))

    def test_checkpoint_match_rejects_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: checkpoint_match
    source: artifacts/screen.png
    template: templates/ok.png
    threshold: 1.5
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ScriptError, "threshold"):
                load_script(script_path)

    def test_gesture_steps_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: swipe
    x1: 10
    y1: 20
    x2: 30
    y2: 40
    duration_ms: 500
    label: scroll list
  - type: drag
    x1: 50
    y1: 60
    x2: 70
    y2: 80
    duration_ms: 900
    label: move slider
  - type: scroll
    direction: down
    distance: 700
    duration_ms: 400
    label: scroll quest list
  - type: back
    label: close panel
""",
                encoding="utf-8",
            )

            script = load_script(script_path)

            self.assertIsInstance(script.steps[0], SwipeStep)
            self.assertIsInstance(script.steps[1], DragStep)
            self.assertIsInstance(script.steps[2], ScrollStep)
            self.assertIsInstance(script.steps[3], BackStep)
            self.assertEqual(script.steps[2].direction, "down")

    def test_gesture_validation_rejects_bad_values(self):
        cases = [
            ("swipe", "x1: -1\n    y1: 0\n    x2: 1\n    y2: 1\n    duration_ms: 300", "non-negative"),
            ("swipe", "x1: 0\n    y1: 0\n    x2: 1\n    y2: 1\n    duration_ms: 10", "duration_ms"),
            ("scroll", "direction: diagonal", "direction"),
            ("scroll", "direction: down\n    distance: 0", "distance"),
        ]
        for step_type, body, message in cases:
            with self.subTest(step_type=step_type, body=body):
                with tempfile.TemporaryDirectory() as tmp:
                    script_path = Path(tmp) / "script.yml"
                    script_path.write_text(f"steps:\n  - type: {step_type}\n    {body}\n", encoding="utf-8")

                    with self.assertRaisesRegex(ScriptError, message):
                        load_script(script_path)


if __name__ == "__main__":
    unittest.main()
