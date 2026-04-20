from pathlib import Path
import tempfile
import unittest

from autoplay.adb import AdbResult
from autoplay.runner import Runner, RunnerError
from autoplay.script import AutoplayScript, CheckpointExistsStep, CheckpointMatchStep, ScreenshotStep, ScriptProfile, TapStep
from png_helpers import write_rgba_png


class FakeAdb:
    def __init__(self, fail_screenshot: bool = False, fail_tap: bool = False):
        self.fail_screenshot = fail_screenshot
        self.fail_tap = fail_tap
        self.taps = []

    def tap(self, x, y, dry_run=False):
        self.taps.append((x, y, dry_run))
        if self.fail_tap:
            return AdbResult(command=["adb", "tap"], returncode=1, stderr="tap failed")
        return AdbResult(command=["adb", "tap"], returncode=0, dry_run=dry_run)

    def screencap(self, out_path: Path):
        if self.fail_screenshot:
            return AdbResult(command=["adb", "screencap"], returncode=1, stderr="boom")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"png")
        return AdbResult(command=["adb", "screencap"], returncode=0, stdout=b"png")


class RunnerTest(unittest.TestCase):
    def test_runner_tap_dry_run_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[
                    ScreenshotStep(out=screenshot),
                    CheckpointExistsStep(path=screenshot),
                    TapStep(x=10, y=20),
                ],
            )
            fake_adb = FakeAdb()

            report = Runner(fake_adb, dry_run_taps=True).run_script(script)

            self.assertEqual(fake_adb.taps, [(10, 20, True)])
            self.assertEqual(report.executed[-1], "3: tap 10,20")

    def test_runner_stops_on_failed_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[ScreenshotStep(out=tmp_path / "screen.png")],
            )

            with self.assertRaisesRegex(RunnerError, "screenshot step"):
                Runner(FakeAdb(fail_screenshot=True)).run_script(script)

    def test_runner_stops_on_missing_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[CheckpointExistsStep(path=tmp_path / "missing.png")],
            )

            with self.assertRaisesRegex(RunnerError, "file does not exist"):
                Runner(FakeAdb()).run_script(script)

    def test_runner_accepts_matching_template_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(255, 0, 0, 255)])
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[CheckpointMatchStep(source=source, template=template, threshold=1.0)],
            )

            report = Runner(FakeAdb()).run_script(script)

            self.assertEqual(report.executed, [f"1: checkpoint_match {template}"])
            self.assertEqual(report.status, "ok")
            self.assertEqual(report.events[0].metadata["score"], 1.0)

    def test_runner_stops_on_template_checkpoint_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(0, 0, 255, 255)])
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[CheckpointMatchStep(source=source, template=template, threshold=1.0)],
            )

            with self.assertRaisesRegex(RunnerError, "best score") as context:
                Runner(FakeAdb()).run_script(script)

            self.assertIsNotNone(context.exception.report)
            self.assertEqual(context.exception.report.status, "error")
            self.assertEqual(context.exception.report.events[-1].status, "error")

    def test_runner_report_to_dict_is_json_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[TapStep(x=10, y=20)],
            )

            report = Runner(FakeAdb(), dry_run_taps=True).run_script(script).to_dict()

            self.assertEqual(report["status"], "ok")
            self.assertTrue(report["dry_run_taps"])
            self.assertEqual(report["events"][0]["step_type"], "tap")
            self.assertEqual(report["adb_results"][0]["dry_run"], True)

    def test_adb_failure_report_includes_error_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = AutoplayScript(
                profile=ScriptProfile(),
                source_path=tmp_path / "script.yml",
                steps=[TapStep(x=10, y=20)],
            )

            with self.assertRaisesRegex(RunnerError, "tap failed") as context:
                Runner(FakeAdb(fail_tap=True)).run_script(script)

            report = context.exception.report.to_dict()
            self.assertEqual(report["status"], "error")
            self.assertEqual(report["events"][0]["status"], "error")
            self.assertEqual(report["events"][0]["metadata"]["returncode"], 1)


if __name__ == "__main__":
    unittest.main()
