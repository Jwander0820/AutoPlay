from pathlib import Path
import json
import tempfile
import unittest

from autoplay.agent_runner import agent_run_script
from autoplay.agent_tools import SafetyError
from autoplay.runner import RunnerError


class AgentRunnerTest(unittest.TestCase):
    def test_agent_run_writes_default_report_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "daily.yml"
            script.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            summary = agent_run_script(script, artifact_root=tmp_path / "artifacts")

            self.assertTrue(summary.validation.ok)
            self.assertEqual(summary.report.status, "ok")
            self.assertTrue(summary.report.dry_run_taps)
            self.assertTrue(summary.report_path.exists())
            self.assertTrue(summary.audit_path.exists())
            report = json.loads(summary.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ok")
            audit_lines = summary.audit_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(audit_lines), 2)

    def test_agent_run_stops_on_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "daily.yml"
            script.write_text(
                """
steps:
  - type: checkpoint_exists
    path: artifacts/missing.png
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RunnerError, "Agent validation failed"):
                agent_run_script(script, artifact_root=tmp_path / "artifacts")

    def test_execute_taps_requires_agent_policy_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "daily.yml"
            script.write_text(
                """
steps:
  - type: tap
    x: 1
    y: 2
    label: open daily panel
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SafetyError, "Real tap execution"):
                agent_run_script(script, artifact_root=tmp_path / "artifacts", execute_taps=True)


if __name__ == "__main__":
    unittest.main()
