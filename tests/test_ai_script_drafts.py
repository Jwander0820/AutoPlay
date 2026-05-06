from pathlib import Path
import tempfile
import unittest

from autoplay.ai_script_drafts import draft_script_file
from autoplay.script import ScriptError


class AiScriptDraftsTest(unittest.TestCase):
    def test_draft_script_writes_and_validates_under_script_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scripts"
            script = root / "ai-draft.yml"

            result = draft_script_file(
                script,
                steps=[{"type": "wait", "seconds": 0}, {"type": "tap", "x": 1, "y": 2, "label": "open panel"}],
                script_root=root,
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.step_count, 2)
            self.assertIn("type: tap", script.read_text(encoding="utf-8"))

    def test_draft_script_rejects_paths_outside_script_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with self.assertRaisesRegex(ScriptError, "under"):
                draft_script_file(tmp_path / "outside.yml", steps=[{"type": "wait", "seconds": 0}], script_root=tmp_path / "scripts")

    def test_draft_script_rejects_private_adb_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scripts"

            with self.assertRaisesRegex(ScriptError, "profile.adb_path"):
                draft_script_file(
                    root / "private.yml",
                    steps=[{"type": "wait", "seconds": 0}],
                    profile={"adb_path": "C:/private/adb.exe"},
                    script_root=root,
                )

    def test_draft_script_requires_overwrite_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scripts"
            script = root / "existing.yml"
            draft_script_file(script, steps=[{"type": "wait", "seconds": 0}], script_root=root)

            with self.assertRaisesRegex(ScriptError, "overwrite=true"):
                draft_script_file(script, steps=[{"type": "wait", "seconds": 0}], script_root=root)

    def test_draft_script_can_use_yaml_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scripts"
            script = root / "from-yaml.yml"

            result = draft_script_file(script, yaml_text="steps:\n  - type: wait\n    seconds: 0\n", script_root=root)

            self.assertTrue(result.ok)
            data = script.read_text(encoding="utf-8")
            self.assertIn("seconds: 0", data)

if __name__ == "__main__":
    unittest.main()
