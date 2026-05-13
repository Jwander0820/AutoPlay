from pathlib import Path
import json
from io import StringIO
import tempfile
import unittest
from unittest import mock

from autoplay.adb import AdbResult
from autoplay.cli import main
from png_helpers import write_rgba_png


class CliTest(unittest.TestCase):
    def test_validate_returns_zero_for_valid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["validate", str(script_path)]), 0)

    def test_validate_returns_one_for_invalid_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"
            script_path.write_text(
                """
steps:
  - type: checkpoint_exists
    path: artifacts/missing.png
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["validate", str(script_path)]), 1)

    def test_match_returns_zero_when_template_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["match", str(source), str(template), "--threshold", "1"]), 0)

    def test_match_returns_one_when_template_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            template = tmp_path / "template.png"
            write_rgba_png(source, 1, 1, [(255, 0, 0, 255)])
            write_rgba_png(template, 1, 1, [(0, 0, 255, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["match", str(source), str(template), "--threshold", "1"]), 1)

    def test_run_writes_report_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            report_path = tmp_path / "report.json"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["run", str(script_path), "--report-out", str(report_path)]), 0)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["events"][0]["step_type"], "wait")

    def test_gesture_commands_default_to_dry_run(self):
        with mock.patch("builtins.print"):
            self.assertEqual(main(["swipe", "10", "20", "30", "40", "--duration-ms", "500"]), 0)
            self.assertEqual(main(["drag", "10", "20", "30", "40", "--duration-ms", "900"]), 0)
            self.assertEqual(main(["scroll", "down", "--distance", "700", "--duration-ms", "400"]), 0)
            self.assertEqual(main(["back"]), 0)

    def test_scroll_can_use_calibration_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            calibration = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            calibration.parent.mkdir(parents=True)
            calibration.write_text(
                json.dumps(
                    {
                        "serial": "emulator-5554",
                        "screen_width": 1200,
                        "screen_height": 2000,
                        "scroll_vertical_distance": 820,
                        "scroll_horizontal_distance": 560,
                    }
                ),
                encoding="utf-8",
            )

            stdout = StringIO()
            with mock.patch("sys.stdout", stdout):
                self.assertEqual(
                    main(["scroll", "down", "--calibrated", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]),
                    0,
                )

            output = stdout.getvalue()
            self.assertIn("shell input swipe 600 590 600 1410 400", output)
            self.assertIn("-s emulator-5554", output)

    def test_calibration_write_and_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"

            with mock.patch("builtins.print"):
                self.assertEqual(
                    main(
                        [
                            "calibration",
                            "write",
                            "--serial",
                            "emulator-5554",
                            "--artifact-root",
                            str(artifact_root),
                            "--screen-width",
                            "1200",
                            "--screen-height",
                            "2000",
                            "--scroll-vertical-distance",
                            "820",
                            "--scroll-horizontal-distance",
                            "560",
                        ]
                    ),
                    0,
                )

            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            self.assertTrue(path.exists())
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 1200)
            self.assertEqual(written["scroll_horizontal_distance"], 560)

            stdout = StringIO()
            with mock.patch("sys.stdout", stdout):
                self.assertEqual(main(["calibration", "show", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]), 0)

            output = stdout.getvalue()
            self.assertIn("Loaded: true", output)
            self.assertIn("screen: 1200x2000", output)

            json_stdout = StringIO()
            with mock.patch("sys.stdout", json_stdout):
                self.assertEqual(main(["calibration", "show", "--json", "--serial", "emulator-5554", "--artifact-root", str(artifact_root)]), 0)

            shown = json.loads(json_stdout.getvalue())
            self.assertTrue(shown["loaded"])
            self.assertEqual(shown["screen_width"], 1200)

    def test_calibration_write_rejects_bad_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("sys.stderr", new_callable=StringIO) as stderr:
                self.assertEqual(
                    main(["calibration", "write", "--artifact-root", tmp, "--screen-width", "0"]),
                    1,
                )

            self.assertIn("screen_width must be a positive integer", stderr.getvalue())

    def test_calibration_write_can_infer_screen_size_from_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / "artifacts"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 3, 2, [(255, 0, 0, 255)] * 6)

            with mock.patch("builtins.print"):
                self.assertEqual(
                    main(["calibration", "write", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--from-screenshot", str(screenshot)]),
                    0,
                )

            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 3)
            self.assertEqual(written["screen_height"], 2)

    def test_calibration_guide_saves_profile_and_notes_without_real_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact_root = tmp_path / "artifacts"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 4, 3, [(255, 0, 0, 255)] * 12)
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe", "2", "1", "2", "2", "400"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("short\nok\n560\nok\nyes\ncalibrated on laptop\n")),
                mock.patch("sys.stdout", StringIO()),
            ):
                self.assertEqual(
                    main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--from-screenshot", str(screenshot)]),
                    0,
                )

            self.assertEqual(execute_flags, [False, False, False, False])
            path = artifact_root / "calibration" / "bluestacks-emulator-5554.json"
            note = artifact_root / "calibration" / "bluestacks-emulator-5554-notes.md"
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["screen_width"], 4)
            self.assertEqual(written["screen_height"], 3)
            self.assertEqual(written["scroll_vertical_distance"], 780)
            self.assertEqual(written["scroll_horizontal_distance"], 560)
            self.assertIn("calibrated on laptop", note.read_text(encoding="utf-8"))

    def test_calibration_guide_requires_yes_prompt_for_real_scroll(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("yes\nok\n\nok\nyes\n\n")),
                mock.patch("sys.stdout", StringIO()),
            ):
                self.assertEqual(
                    main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--yes"]),
                    0,
                )

            self.assertEqual(execute_flags, [False, True, False])

    def test_calibration_guide_keeps_invalid_feedback_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "artifacts"
            execute_flags = []

            def fake_scroll(*args, **kwargs):
                execute_flags.append(kwargs.get("execute", False))
                return AdbResult(command=["adb", "shell", "input", "swipe"], returncode=0, dry_run=not kwargs.get("execute", False))

            with (
                mock.patch("autoplay.cli.api.scroll", side_effect=fake_scroll),
                mock.patch("sys.stdin", StringIO("banana\nok\nok\nyes\n\n")),
                mock.patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                self.assertEqual(main(["calibration", "guide", "--serial", "emulator-5554", "--artifact-root", str(artifact_root), "--max-rounds", "2"]), 0)

            self.assertEqual(execute_flags, [False, False, False])
            self.assertIn("Invalid feedback", stdout.getvalue())

    def test_calibration_guide_reports_missing_interactive_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch("sys.stdin", StringIO("")),
                mock.patch("sys.stdout", StringIO()),
                mock.patch("sys.stderr", new_callable=StringIO) as stderr,
            ):
                self.assertEqual(main(["calibration", "guide", "--artifact-root", tmp]), 1)

            self.assertIn("calibration guide requires interactive input", stderr.getvalue())

    def test_calibration_guide_rejects_invalid_max_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch("sys.stdout", StringIO()),
                mock.patch("sys.stderr", new_callable=StringIO) as stderr,
            ):
                self.assertEqual(main(["calibration", "guide", "--artifact-root", tmp, "--max-rounds", "0"]), 1)

            self.assertIn("--max-rounds must be a positive integer", stderr.getvalue())

    def test_record_appends_step_from_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.yml"

            with mock.patch("sys.stdin", StringIO("wait 0\ndone\n")), mock.patch("sys.stdout", StringIO()):
                self.assertEqual(main(["record", str(script_path)]), 0)

            self.assertIn("type: wait", script_path.read_text(encoding="utf-8"))

    def test_agent_run_writes_report_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "script.yml"
            artifact_root = tmp_path / "artifacts"
            script_path.write_text(
                """
steps:
  - type: wait
    seconds: 0
""",
                encoding="utf-8",
            )

            with mock.patch("builtins.print"):
                self.assertEqual(main(["agent-run", str(script_path), "--artifact-root", str(artifact_root)]), 0)

            self.assertTrue((artifact_root / "reports" / "script-agent-dry-run.json").exists())
            self.assertTrue((artifact_root / "agent" / "script-audit.jsonl").exists())

    def test_ai_tool_runs_json_request_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request = tmp_path / "request.json"
            response_out = tmp_path / "response.json"
            request.write_text(json.dumps({"tool": "tap", "args": {"x": 1, "y": 2}}), encoding="utf-8")
            bridge = mock.Mock()
            bridge.handle.return_value = {"ok": True, "tool": "tap", "result": {"dry_run": True}, "messages": []}

            with mock.patch("autoplay.cli.AiBridge.from_local_config", return_value=bridge):
                self.assertEqual(main(["ai-tool", str(request), "--out", str(response_out), "--artifact-root", str(tmp_path / "artifacts")]), 0)

            bridge.handle.assert_called_once_with({"tool": "tap", "args": {"x": 1, "y": 2}})
            written = json.loads(response_out.read_text(encoding="utf-8"))
            self.assertEqual(written["tool"], "tap")
            self.assertTrue(written["ok"])

    def test_ai_server_starts_and_closes_on_keyboard_interrupt(self):
        server = mock.Mock()
        server.serve_forever.side_effect = KeyboardInterrupt()
        ready = mock.Mock(server=server, url="http://127.0.0.1:8787/")

        with mock.patch("autoplay.cli.create_ai_tool_server", return_value=ready) as create_server, mock.patch("builtins.print"):
            self.assertEqual(main(["ai-server", "--port", "0", "--artifact-root", "artifacts"]), 0)

        create_server.assert_called_once()
        config = create_server.call_args.args[0]
        self.assertEqual(config.port, 0)
        self.assertEqual(str(config.artifact_root), "artifacts")
        server.server_close.assert_called_once()

    def test_ai_server_generates_device_input_code_when_real_input_is_enabled(self):
        server = mock.Mock()
        server.serve_forever.side_effect = KeyboardInterrupt()
        ready = mock.Mock(server=server, url="http://127.0.0.1:8787/")

        with (
            mock.patch("autoplay.cli.create_ai_tool_server", return_value=ready) as create_server,
            mock.patch("autoplay.cli._generate_device_input_code", return_value="RUN-123"),
            mock.patch("builtins.print") as printer,
        ):
            self.assertEqual(main(["ai-server", "--port", "0", "--allow-device-input"]), 0)

        config = create_server.call_args.args[0]
        self.assertTrue(config.allow_device_input)
        self.assertEqual(config.device_input_code, "RUN-123")
        printed = "\n".join(str(call.args[0]) for call in printer.call_args_list)
        self.assertIn("Device input code: RUN-123", printed)

    def test_ai_schemas_writes_machine_readable_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "schemas.json"

            self.assertEqual(main(["ai-schemas", "--out", str(out)]), 0)

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            tools = {tool["name"]: tool for tool in payload["tools"]}
            self.assertIn("tap", tools)
            self.assertEqual(tools["tap"]["request_schema"]["properties"]["tool"]["const"], "tap")

    def test_ai_examples_writes_machine_readable_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "examples.json"

            self.assertEqual(main(["ai-examples", "--out", str(out)]), 0)

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            examples = {example["name"]: example for example in payload["examples"]}
            self.assertEqual(examples["dry_run_tap"]["request"]["tool"], "tap")
            self.assertEqual(examples["guarded_real_tap"]["request"]["args"]["device_input_code"], "CODE-SHOWN-IN-LAUNCHER")

    def test_ai_chat_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "chat.json"
            transcript = Path(tmp) / "transcript.json"
            chat_result = mock.Mock()
            chat_result.ok = True
            chat_result.transcript = [{"type": "request"}]
            chat_result.to_dict.return_value = {"ok": True, "provider": "ollama", "final_message": "done", "transcript": chat_result.transcript}

            with (
                mock.patch("autoplay.cli.AiBridge.from_local_config", return_value=mock.Mock()) as bridge,
                mock.patch("autoplay.cli.run_ai_chat", return_value=chat_result) as chat,
            ):
                self.assertEqual(
                    main(
                        [
                            "ai-chat",
                            "--provider",
                            "lm-studio",
                            "--model",
                            "llama3.1",
                            "--prompt",
                            "draft a script",
                            "--tool",
                            "draft_script",
                            "--transcript-out",
                            str(transcript),
                            "--out",
                            str(out),
                        ]
                    ),
                    0,
                )

            self.assertEqual(chat.call_args.args[0], "draft a script")
            self.assertEqual(chat.call_args.args[1].provider, "lm-studio")
            self.assertEqual(chat.call_args.args[1].allowed_tools, ("draft_script",))
            bridge.assert_called_once()
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["provider"], "ollama")
            transcript_payload = json.loads(transcript.read_text(encoding="utf-8"))
            self.assertEqual(transcript_payload["transcript"], [{"type": "request"}])

    def test_ai_chat_smoke_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "chat-smoke.json"
            transcript = Path(tmp) / "chat-smoke-transcript.json"
            chat_result = mock.Mock()
            chat_result.ok = True
            chat_result.transcript = [{"type": "request", "tools": ["draft_script"]}]
            chat_result.to_dict.return_value = {"ok": True, "provider": "fake", "final_message": "done", "transcript": chat_result.transcript}

            with mock.patch("autoplay.cli.run_ai_chat", return_value=chat_result) as chat:
                self.assertEqual(main(["ai-chat-smoke", "--out", str(out), "--transcript-out", str(transcript)]), 0)

            self.assertEqual(chat.call_args.args[1].provider, "fake")
            self.assertEqual(chat.call_args.args[1].model, "draft_script")
            self.assertEqual(chat.call_args.args[1].allowed_tools, ("draft_script", "validate"))
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["provider"], "fake")
            transcript_payload = json.loads(transcript.read_text(encoding="utf-8"))
            self.assertEqual(transcript_payload["transcript"][0]["tools"], ["draft_script"])

    def test_ai_adapter_writes_machine_readable_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "adapter.json"

            self.assertEqual(main(["ai-adapter", "--prefix-names", "--out", str(out)]), 0)

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            tools = {tool["name"]: tool for tool in payload["tools"]}
            self.assertIn("autoplay.tap", tools)
            self.assertEqual(tools["autoplay.tap"]["bridge_request"]["tool"], "tap")
            self.assertIn("inputSchema", tools["autoplay.tap"])

    def test_ai_mcp_stdio_delegates_to_stdio_server(self):
        with mock.patch("autoplay.cli.run_mcp_stdio", return_value=0) as server:
            self.assertEqual(main(["ai-mcp-stdio", "--artifact-root", "artifacts", "--step-budget", "3"]), 0)

        config = server.call_args.args[0]
        self.assertEqual(str(config.artifact_root), "artifacts")
        self.assertEqual(config.step_budget, 3)

    def test_ai_mcp_smoke_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "mcp-smoke.json"
            smoke_result = mock.Mock()
            smoke_result.ok = True
            smoke_result.to_dict.return_value = {"ok": True, "protocol_version": "2025-11-25", "tool_count": 10}

            with mock.patch("autoplay.cli.run_ai_mcp_smoke", return_value=smoke_result) as smoke:
                self.assertEqual(main(["ai-mcp-smoke", "--example", "dry_run_tap", "--out", str(out)]), 0)

            config = smoke.call_args.args[0]
            self.assertEqual(str(config.artifact_root), "artifacts")
            self.assertEqual(smoke.call_args.kwargs["example_name"], "dry_run_tap")
            self.assertFalse(smoke.call_args.kwargs["allow_real_examples"])
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["protocol_version"], "2025-11-25")

    def test_ai_smoke_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "smoke.json"
            smoke_result = mock.Mock()
            smoke_result.ok = True
            smoke_result.to_dict.return_value = {"ok": True, "schema_count": 10, "example_count": 7}

            with mock.patch("autoplay.cli.run_ai_client_smoke", return_value=smoke_result) as smoke:
                self.assertEqual(main(["ai-smoke", "--base-url", "http://127.0.0.1:8787", "--example", "dry_run_tap", "--out", str(out)]), 0)

            smoke.assert_called_once_with(
                base_url="http://127.0.0.1:8787",
                example_name="dry_run_tap",
                timeout=3.0,
                allow_real_examples=False,
            )
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_count"], 10)

    def test_screenshot_multiple_devices_prints_serial_hint(self):
        result = AdbResult(command=["adb", "exec-out", "screencap", "-p"], returncode=1, stderr="error: more than one device/emulator")
        doctor_report = mock.Mock(lines=["Connected devices: emulator-5554, 127.0.0.1:5555"])

        with (
            mock.patch("autoplay.cli.api.screenshot", return_value=result),
            mock.patch("autoplay.cli.api.doctor", return_value=doctor_report),
            mock.patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            self.assertEqual(main(["screenshot", "--out", "artifacts/manual/screen.png"]), 1)

        output = stderr.getvalue()
        self.assertIn("more than one device/emulator", output)
        self.assertIn("--serial emulator-5554", output)
        self.assertIn("--serial 127.0.0.1:5555", output)

    def test_click_map_writes_html_from_existing_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["click-map", str(screenshot), "--out", str(html)]), 0)

            html_text = html.read_text(encoding="utf-8")
            self.assertIn("AutoPlay 錄製工作台", html_text)
            self.assertIn("互動工具", html_text)
            self.assertIn("快速補步驟與手勢微調", html_text)

    def test_click_map_uses_script_out_download_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            screenshot = tmp_path / "screen.png"
            html = tmp_path / "screen-clicks.html"
            script = tmp_path / "my-daily.yml"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("builtins.print"):
                self.assertEqual(main(["click-map", str(screenshot), "--out", str(html), "--script-out", str(script)]), 0)

            self.assertIn('const scriptFilename = "my-daily.yml"', html.read_text(encoding="utf-8"))

    def test_record_ui_starts_and_stops_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "daily.yml"
            screenshot = tmp_path / "screen.png"
            write_rgba_png(screenshot, 1, 1, [(255, 0, 0, 255)])

            with mock.patch("autoplay.cli.create_recorder_server") as create_server, mock.patch("builtins.print") as printer:
                server = create_server.return_value.server
                server.serve_forever.side_effect = KeyboardInterrupt()
                self.assertEqual(main(["record-ui", str(script), "--screenshot", str(screenshot), "--port", "0", "--allow-device-input"]), 0)

            create_server.assert_called_once()
            config = create_server.call_args.args[0]
            self.assertTrue(config.allow_device_input)
            server.server_close.assert_called_once()
            printed = "\n".join(str(call.args[0]) for call in printer.call_args_list)
            self.assertIn("Calibration: defaults", printed)

    def test_record_clicks_delegates_to_live_click_recorder(self):
        with mock.patch("autoplay.cli.run_windows_live_click_recorder", return_value=[]) as recorder, mock.patch("builtins.print"):
            self.assertEqual(main(["record-clicks", "scripts/daily.yml", "--screenshot", "artifacts/manual/start.png", "--max-clicks", "1"]), 0)

        recorder.assert_called_once_with(
            "scripts/daily.yml",
            screenshot_path="artifacts/manual/start.png",
            window_title="BlueStacks",
            label_prefix="live click",
            max_clicks=1,
        )


if __name__ == "__main__":
    unittest.main()
