import unittest
from unittest import mock

from autoplay.ai_adapter import adapter_call_request, get_ai_adapter_manifest, handle_adapter_call
from autoplay.ai_schemas import SUPPORTED_TOOLS


class AiAdapterTest(unittest.TestCase):
    def test_manifest_mirrors_ai_schema_tools(self):
        manifest = get_ai_adapter_manifest()

        self.assertTrue(manifest["ok"])
        self.assertEqual([tool["name"] for tool in manifest["tools"]], list(SUPPORTED_TOOLS))
        tap = next(tool for tool in manifest["tools"] if tool["name"] == "tap")
        self.assertEqual(tap["inputSchema"]["properties"]["execute"]["default"], False)
        self.assertEqual(tap["bridge_request"], {"tool": "tap", "args": "<arguments>"})
        self.assertFalse(tap["annotations"]["readOnlyHint"])

        doctor = next(tool for tool in manifest["tools"] if tool["name"] == "doctor")
        self.assertTrue(doctor["annotations"]["readOnlyHint"])

    def test_manifest_can_prefix_tool_names_for_shared_namespaces(self):
        manifest = get_ai_adapter_manifest(prefix_names=True)

        names = [tool["name"] for tool in manifest["tools"]]

        self.assertIn("autoplay.tap", names)
        self.assertIn("autoplay.draft_script", names)

    def test_adapter_call_request_accepts_prefixed_and_plain_names(self):
        plain = adapter_call_request("tap", {"x": 1, "y": 2})
        prefixed = adapter_call_request("autoplay.tap", {"x": 1, "y": 2})

        self.assertEqual(plain, {"tool": "tap", "args": {"x": 1, "y": 2}})
        self.assertEqual(prefixed, plain)

    def test_adapter_call_rejects_unknown_tools(self):
        with self.assertRaises(ValueError):
            adapter_call_request("autoplay.raw_adb", {})

    def test_handle_adapter_call_routes_through_bridge(self):
        bridge = mock.Mock()
        bridge.handle.return_value = {"ok": True, "tool": "tap"}

        response = handle_adapter_call(bridge, "autoplay.tap", {"x": 1, "y": 2})

        self.assertTrue(response["ok"])
        bridge.handle.assert_called_once_with({"tool": "tap", "args": {"x": 1, "y": 2}})


if __name__ == "__main__":
    unittest.main()
