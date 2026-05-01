from pathlib import Path
import json
import tempfile
import unittest

from autoplay.calibration import CalibrationProfile, calibration_path_for_serial, load_calibration_for_serial, load_calibration_profile, save_calibration_profile


class CalibrationTest(unittest.TestCase):
    def test_load_valid_calibration_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(
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

            profile = load_calibration_profile(path)

            self.assertEqual(profile.serial, "emulator-5554")
            self.assertEqual(profile.screen_width, 1200)
            self.assertEqual(profile.distance_for_direction("down"), 820)
            self.assertEqual(profile.distance_for_direction("left"), 560)
            self.assertEqual(profile.default_swipe_duration_ms, 450)

    def test_missing_calibration_profile_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = load_calibration_for_serial("emulator-5554", artifact_root=tmp)

            self.assertFalse(result.loaded)
            self.assertEqual(result.profile.serial, "emulator-5554")
            self.assertEqual(result.profile.screen_width, 1080)
            self.assertEqual(result.profile.scroll_vertical_distance, 700)
            self.assertTrue(result.path.as_posix().endswith("bluestacks-emulator-5554.json"))

    def test_malformed_calibration_profile_returns_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = calibration_path_for_serial(tmp, "emulator-5554")
            path.parent.mkdir(parents=True)
            path.write_text("{broken", encoding="utf-8")

            result = load_calibration_for_serial("emulator-5554", artifact_root=tmp)

            self.assertFalse(result.loaded)
            self.assertTrue(result.warnings)
            self.assertEqual(result.profile.screen_height, 1920)

    def test_save_calibration_profile_writes_reviewable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            profile = CalibrationProfile(serial="device", screen_width=1000, screen_height=1600)

            save_calibration_profile(profile, path)

            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["serial"], "device")
            self.assertEqual(written["screen_height"], 1600)


if __name__ == "__main__":
    unittest.main()
