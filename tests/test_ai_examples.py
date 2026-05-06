import json
import unittest

from autoplay.ai_examples import get_ai_examples_payload


class AiExamplesTest(unittest.TestCase):
    def test_examples_payload_contains_safe_canonical_requests(self):
        payload = get_ai_examples_payload()

        self.assertTrue(payload["ok"])
        examples = {example["name"]: example for example in payload["examples"]}
        self.assertIn("doctor", examples)
        self.assertIn("screenshot", examples)
        self.assertIn("dry_run_tap", examples)
        self.assertIn("guarded_real_tap", examples)
        self.assertIn("dry_run_scroll", examples)
        self.assertIn("validate_script", examples)
        self.assertIn("draft_script", examples)
        self.assertIn("dry_run_script", examples)
        self.assertEqual(examples["dry_run_tap"]["request"]["tool"], "tap")
        self.assertNotIn("execute", examples["dry_run_tap"]["request"]["args"])
        self.assertEqual(examples["guarded_real_tap"]["request"]["args"]["device_input_code"], "CODE-SHOWN-IN-LAUNCHER")
        self.assertEqual(examples["draft_script"]["request"]["tool"], "draft_script")

    def test_examples_do_not_include_private_local_values(self):
        text = json.dumps(get_ai_examples_payload(), sort_keys=True)

        self.assertNotIn("C:\\Software\\LDPlayer", text)
        self.assertNotIn("Software\\\\LDPlayer", text)
        self.assertNotIn("user@example.com", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("token", text.lower())

    def test_examples_return_copies(self):
        first = get_ai_examples_payload()
        first["examples"][0]["request"]["args"]["mutated"] = True

        second = get_ai_examples_payload()

        self.assertNotIn("mutated", second["examples"][0]["request"]["args"])


if __name__ == "__main__":
    unittest.main()
