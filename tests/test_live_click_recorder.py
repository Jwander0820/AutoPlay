from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml

from autoplay.live_click_recorder import ClientGeometry, LiveClickRecorderError, append_live_click, map_click_to_target, run_windows_live_click_recorder


class LiveClickRecorderTest(unittest.TestCase):
    def test_map_click_to_target_scales_client_coordinates(self):
        geometry = ClientGeometry(left=100, top=50, width=400, height=300, target_width=800, target_height=600)

        self.assertEqual(map_click_to_target(300, 200, geometry), (400, 300))

    def test_map_click_to_target_ignores_outside_clicks(self):
        geometry = ClientGeometry(left=100, top=50, width=400, height=300, target_width=800, target_height=600)

        self.assertIsNone(map_click_to_target(99, 200, geometry))
        self.assertIsNone(map_click_to_target(300, 351, geometry))

    def test_append_live_click_writes_tap_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.yml"

            append_live_click(script, 10, 20, "live click 1")

            data = yaml.safe_load(script.read_text(encoding="utf-8"))
            self.assertEqual(data["steps"], [{"type": "tap", "x": 10, "y": 20, "label": "live click 1"}])

    def test_run_windows_live_click_recorder_requires_windows(self):
        with mock.patch("sys.platform", "linux"):
            with self.assertRaisesRegex(LiveClickRecorderError, "Windows Python"):
                run_windows_live_click_recorder("script.yml")


if __name__ == "__main__":
    unittest.main()
