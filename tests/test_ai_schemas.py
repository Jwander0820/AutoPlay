import unittest

from autoplay.ai_schemas import SUPPORTED_TOOLS, get_ai_schema_payload, get_ai_tool_schemas


class AiSchemasTest(unittest.TestCase):
    def test_schema_payload_lists_supported_tools_with_request_schemas(self):
        payload = get_ai_schema_payload()

        self.assertTrue(payload["ok"])
        self.assertIn("schema_version", payload)
        tools = {tool["name"]: tool for tool in payload["tools"]}
        self.assertEqual(tuple(tools), SUPPORTED_TOOLS)
        self.assertEqual(tools["tap"]["request_schema"]["properties"]["tool"]["const"], "tap")
        self.assertEqual(tools["tap"]["args_schema"]["properties"]["execute"]["default"], False)
        self.assertIn("device_input_code", tools["tap"]["args_schema"]["properties"])
        self.assertEqual(tools["tap"]["safety"], "device_input_guarded")
        self.assertEqual(tools["draft_script"]["safety"], "write_reviewable_script")
        self.assertIn("steps", tools["draft_script"]["args_schema"]["properties"])
        self.assertIn("direction", tools["scroll"]["args_schema"]["required"])

    def test_tool_schemas_return_copies(self):
        first = get_ai_tool_schemas()
        first[0]["args_schema"]["properties"]["mutated"] = {"type": "string"}

        second = get_ai_tool_schemas()

        self.assertNotIn("mutated", second[0]["args_schema"]["properties"])


if __name__ == "__main__":
    unittest.main()
