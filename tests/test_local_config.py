import unittest
from pathlib import Path

from autoplay.local_config import LocalConfig, load_local_config, save_local_config


class LocalConfigTest(unittest.TestCase):
    def test_missing_config_uses_defaults(self):
        config = load_local_config(Path("config") / "__missing_for_test.local.json")

        self.assertEqual(config.script_path, "scripts/ldplayer-test.yml")
        self.assertEqual(config.screenshot_path, "artifacts/manual/ldplayer-start.png")
        self.assertEqual(config.recorder_port, 0)
        self.assertTrue(config.allow_device_input)

    def test_save_and_load_config(self):
        path = Path("config") / "__test_autoplay.local.json"
        saved = LocalConfig(
            emulator_profile="ldplayer",
            adb_path=r"C:\Private\LDPlayer\adb.exe",
            serial="emulator-5554",
            connect_targets=("127.0.0.1:5555",),
            script_path="scripts/test.yml",
            screenshot_path="artifacts/manual/test.png",
            recorder_port=8765,
            allow_device_input=False,
        )

        try:
            save_local_config(saved, path)
            loaded = load_local_config(path)
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(loaded, saved)

    def test_invalid_values_keep_safe_defaults(self):
        config = LocalConfig.from_dict(
            {
                "emulator_profile": "custom",
                "adb_path": 123,
                "serial": [],
                "connect_targets": ["127.0.0.1:5555", 123, ""],
                "script_path": "scripts/custom.yml",
                "screenshot_path": "artifacts/manual/custom.png",
                "recorder_port": -1,
                "allow_device_input": "yes",
            }
        )

        self.assertIsNone(config.adb_path)
        self.assertIsNone(config.serial)
        self.assertEqual(config.emulator_profile, "custom")
        self.assertEqual(config.connect_targets, ("127.0.0.1:5555",))
        self.assertEqual(config.script_path, "scripts/custom.yml")
        self.assertEqual(config.screenshot_path, "artifacts/manual/custom.png")
        self.assertEqual(config.recorder_port, 0)
        self.assertTrue(config.allow_device_input)


if __name__ == "__main__":
    unittest.main()
