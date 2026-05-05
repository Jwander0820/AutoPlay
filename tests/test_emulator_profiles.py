import unittest

from autoplay.emulator_profiles import get_profile, profile_id_to_label, profile_label_to_id


class EmulatorProfilesTest(unittest.TestCase):
    def test_ldplayer_profile_has_connect_targets(self):
        profile = get_profile("ldplayer")

        self.assertEqual(profile.id, "ldplayer")
        self.assertIn("127.0.0.1:5555", profile.connect_targets)
        self.assertTrue(any(candidate.endswith(r"LDPlayer9\adb.exe") for candidate in profile.adb_candidates))

    def test_unknown_profile_falls_back_to_ldplayer(self):
        self.assertEqual(get_profile("unknown").id, "ldplayer")

    def test_label_mapping(self):
        label = profile_id_to_label("bluestacks")

        self.assertEqual(profile_label_to_id(label), "bluestacks")


if __name__ == "__main__":
    unittest.main()
