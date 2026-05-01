import unittest

from autoplay.adb import AdbClient, parse_device_serials


class AdbClientTest(unittest.TestCase):
    def test_build_command_without_serial(self):
        client = AdbClient("adb")

        self.assertEqual(client.build_command(["devices", "-l"]), ["adb", "devices", "-l"])

    def test_build_command_with_serial(self):
        client = AdbClient("adb", serial="emulator-5554")

        self.assertEqual(
            client.build_command(["shell", "input", "tap", "1", "2"]),
            [
                "adb",
                "-s",
                "emulator-5554",
                "shell",
                "input",
                "tap",
                "1",
                "2",
            ],
        )

    def test_parse_device_serials(self):
        output = """List of devices attached
emulator-5554 device product:bluestacks model:BlueStacks device:android
offline-1 offline
"""

        self.assertEqual(parse_device_serials(output), ["emulator-5554"])

    def test_tap_dry_run_does_not_execute(self):
        client = AdbClient("adb")

        result = client.tap(10, 20, dry_run=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.command, ["adb", "shell", "input", "tap", "10", "20"])

    def test_swipe_dry_run_builds_command(self):
        client = AdbClient("adb", serial="emulator-5554")

        result = client.swipe(10, 20, 30, 40, 500, dry_run=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(
            result.command,
            ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "10", "20", "30", "40", "500"],
        )

    def test_back_dry_run_builds_command(self):
        client = AdbClient("adb")

        result = client.back(dry_run=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.command, ["adb", "shell", "input", "keyevent", "BACK"])


if __name__ == "__main__":
    unittest.main()
