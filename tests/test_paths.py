import os
import unittest
from unittest import mock

from autoplay.paths import DEFAULT_WINDOWS_ADB, default_adb_path, resolve_adb_path, windows_path_to_wsl


class PathsTest(unittest.TestCase):
    def test_env_override_wins(self):
        with mock.patch.dict(os.environ, {"AUTOPLAY_ADB": "/custom/adb"}):
            self.assertEqual(resolve_adb_path("profile-adb"), "/custom/adb")

    def test_profile_override_wins_over_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_adb_path("/profile/adb"), "/profile/adb")

    def test_default_adb_path(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("autoplay.paths.path_exists_for_host", return_value=False):
            resolved = resolve_adb_path()

        if os.name == "nt":
            self.assertEqual(resolved, DEFAULT_WINDOWS_ADB)
        else:
            self.assertTrue(resolved.endswith("/Program Files/BlueStacks_nxt/HD-Adb.exe"))

    def test_default_adb_path_uses_first_existing_known_path(self):
        ldplayer = r"C:\LDPlayer\LDPlayer9\adb.exe"

        def fake_exists(path):
            return path == ldplayer

        with mock.patch("autoplay.paths.path_exists_for_host", side_effect=fake_exists):
            self.assertEqual(default_adb_path(), ldplayer)

    def test_windows_path_to_wsl(self):
        self.assertEqual(
            windows_path_to_wsl(r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"),
            "/mnt/c/Program Files/BlueStacks_nxt/HD-Adb.exe",
        )


if __name__ == "__main__":
    unittest.main()
