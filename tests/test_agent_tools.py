from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.agent_tools import AgentPolicy, AgentSession, SafetyError
from autoplay.runner import RunnerReport


class AgentToolsTest(unittest.TestCase):
    def test_tap_defaults_to_dry_run_and_writes_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "artifacts" / "agent" / "audit.jsonl"
            session = AgentSession(policy=AgentPolicy(artifact_root=Path(tmp) / "artifacts", audit_path=audit))

            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0, dry_run=True)) as tap:
                result = session.tap(10, 20, label="open daily panel")

            tap.assert_called_once_with(10, 20, adb_path=None, serial=None, execute=False)
            self.assertTrue(result.dry_run)
            event = _read_audit(audit)[0]
            self.assertEqual(event["tool"], "tap")
            self.assertEqual(event["status"], "ok")
            self.assertEqual(event["steps_used"], 1)

    def test_real_tap_requires_policy_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "artifacts" / "agent" / "audit.jsonl"
            session = AgentSession(policy=AgentPolicy(artifact_root=Path(tmp) / "artifacts", audit_path=audit))

            with self.assertRaisesRegex(SafetyError, "Real device input"):
                session.tap(10, 20, label="open daily panel", execute=True)

            event = _read_audit(audit)[0]
            self.assertEqual(event["status"], "blocked")

    def test_policy_can_allow_real_tap(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "artifacts" / "agent" / "audit.jsonl"
            policy = AgentPolicy(allow_device_input=True, artifact_root=Path(tmp) / "artifacts", audit_path=audit)
            session = AgentSession(policy=policy)

            with mock.patch("autoplay.api.tap", return_value=AdbResult(command=["adb", "tap"], returncode=0)) as tap:
                session.tap(10, 20, label="open daily panel", execute=True)

            tap.assert_called_once_with(10, 20, adb_path=None, serial=None, execute=True)

    def test_step_budget_blocks_after_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "artifacts" / "agent" / "audit.jsonl"
            session = AgentSession(policy=AgentPolicy(step_budget=1, artifact_root=Path(tmp) / "artifacts", audit_path=audit))

            with mock.patch("autoplay.api.validate") as validate:
                session.validate("script.yml")
                with self.assertRaisesRegex(SafetyError, "budget"):
                    session.validate("script.yml")

            self.assertEqual(validate.call_count, 1)
            events = _read_audit(audit)
            self.assertEqual(events[-1]["status"], "blocked")

    def test_artifact_paths_are_required_for_screenshot_match_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            audit = root / "agent" / "audit.jsonl"
            session = AgentSession(policy=AgentPolicy(artifact_root=root, audit_path=audit))

            with self.assertRaisesRegex(SafetyError, "under"):
                session.screenshot(Path(tmp) / "screen.png")
            with self.assertRaisesRegex(SafetyError, "under"):
                session.match(Path(tmp) / "source.png", root / "template.png")
            with self.assertRaisesRegex(SafetyError, "under"):
                session.run(Path(tmp) / "script.yml", report_out=Path(tmp) / "report.json")

    def test_run_blocks_unsafe_script_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audit = tmp_path / "artifacts" / "agent" / "audit.jsonl"
            script = tmp_path / "script.yml"
            script.write_text(
                """
steps:
  - type: tap
    x: 1
    y: 2
    label: purchase pack
""",
                encoding="utf-8",
            )
            session = AgentSession(policy=AgentPolicy(artifact_root=tmp_path / "artifacts", audit_path=audit))

            with self.assertRaisesRegex(SafetyError, "blocked term"):
                session.run(script, report_out=tmp_path / "artifacts" / "reports" / "run.json")

            event = _read_audit(audit)[0]
            self.assertEqual(event["tool"], "run")
            self.assertEqual(event["status"], "blocked")

    def test_run_defaults_to_dry_run_taps(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audit = tmp_path / "artifacts" / "agent" / "audit.jsonl"
            script = tmp_path / "script.yml"
            script.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )
            session = AgentSession(policy=AgentPolicy(artifact_root=tmp_path / "artifacts", audit_path=audit))

            with mock.patch("autoplay.api.run", return_value=RunnerReport(dry_run_taps=True)) as run:
                session.run(script, report_out=tmp_path / "artifacts" / "reports" / "run.json", intent="daily safe routine")

            run.assert_called_once_with(script, execute_taps=False, report_out=tmp_path / "artifacts" / "reports" / "run.json")


def _read_audit(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
