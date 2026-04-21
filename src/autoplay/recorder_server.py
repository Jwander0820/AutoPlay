from __future__ import annotations

import json
import time
import base64
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import api
from .adb import AdbResult
from .agent_runner import agent_run_script
from .agent_tools import SafetyError
from .click_map import render_builder_html
from .runner import RunnerError
from .validation import format_report


@dataclass(frozen=True)
class RecorderServerConfig:
    script_path: Path
    screenshot_path: Path
    host: str = "127.0.0.1"
    port: int = 8765
    allow_device_input: bool = False
    adb_path: str | None = None
    serial: str | None = None


@dataclass(frozen=True)
class RecorderServerReady:
    server: ThreadingHTTPServer
    url: str


@dataclass(frozen=True)
class RecorderUiCapture:
    config: RecorderServerConfig
    screenshot_result: AdbResult | None = None


MAX_POST_BYTES = 1_000_000


def capture_recorder_screenshot(
    script_path: str | Path,
    screenshot_path: str | Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    capture: bool = False,
    adb_path: str | None = None,
    serial: str | None = None,
    allow_device_input: bool = False,
) -> RecorderUiCapture:
    config = RecorderServerConfig(
        script_path=Path(script_path),
        screenshot_path=Path(screenshot_path),
        host=host,
        port=port,
        allow_device_input=allow_device_input,
        adb_path=adb_path,
        serial=serial,
    )
    if not capture:
        return RecorderUiCapture(config=config)
    result = api.screenshot(config.screenshot_path, adb_path=adb_path, serial=serial)
    return RecorderUiCapture(config=config, screenshot_result=result)


def create_recorder_server(config: RecorderServerConfig) -> RecorderServerReady:
    handler = _make_handler(config)
    server = ThreadingHTTPServer((config.host, config.port), handler)
    host, port = server.server_address
    return RecorderServerReady(server=server, url=f"http://{host}:{port}/")


def _make_handler(config: RecorderServerConfig):
    capture_state = {"index": 0, "current_path": config.screenshot_path}

    class RecorderHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "messages": ["Not found."]})
                return
            try:
                html = render_builder_html(
                    config.screenshot_path,
                    config.screenshot_path.read_bytes(),
                    config.script_path,
                    save_url="/api/script",
                    capture_url="/api/capture",
                    tap_capture_url="/api/tap-capture" if config.allow_device_input else None,
                    run_url="/api/run",
                    allow_device_input=config.allow_device_input,
                    profile_adb_path=config.adb_path,
                    profile_serial=config.serial,
                )
            except OSError as exc:
                self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "messages": [str(exc)]})
                return
            self._write_text(HTTPStatus.OK, html, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path == "/api/script":
                self._save_script()
                return
            if self.path == "/api/capture":
                self._capture_latest()
                return
            if self.path == "/api/tap-capture":
                self._tap_capture()
                return
            if self.path == "/api/run":
                self._run_script()
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "messages": ["Not found."]})

        def _save_script(self) -> None:
            payload = self._read_json_payload()
            if payload is None:
                return
            yaml_text = payload.get("yaml")
            if not isinstance(yaml_text, str) or not yaml_text.strip():
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["YAML content is required."]})
                return

            try:
                config.script_path.parent.mkdir(parents=True, exist_ok=True)
                config.script_path.write_text(yaml_text, encoding="utf-8")
            except OSError as exc:
                self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "messages": [f"Cannot write script: {exc}"]})
                return

            report = api.validate(config.script_path)
            messages = format_report(report)
            self._write_json(
                HTTPStatus.OK,
                {"ok": report.ok, "status": "saved", "script_path": str(config.script_path), "messages": messages},
            )

        def _capture_latest(self) -> None:
            screenshot_path = _next_capture_path(config.screenshot_path, capture_state)
            result = api.screenshot(screenshot_path, adb_path=config.adb_path, serial=config.serial)
            if not result.ok:
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "messages": [f"screencap failed with exit {result.returncode}: {result.stderr}"]},
                )
                return
            capture_state["current_path"] = screenshot_path
            self._write_json(HTTPStatus.OK, _screenshot_payload(screenshot_path, steps=[{"type": "screenshot", "out": screenshot_path.as_posix()}]))

        def _tap_capture(self) -> None:
            if not config.allow_device_input:
                self._write_json(HTTPStatus.FORBIDDEN, {"ok": False, "messages": ["Device input is not enabled for this recorder."]})
                return
            payload = self._read_json_payload()
            if payload is None:
                return
            try:
                x = int(payload["x"])
                y = int(payload["y"])
                label = str(payload.get("label") or "recorded tap")
                wait_seconds = float(payload.get("wait_seconds", 1))
                auto_wait = bool(payload.get("auto_wait", False))
                min_wait_seconds = float(payload.get("min_wait_seconds", 1))
                max_wait_seconds = float(payload.get("max_wait_seconds", 12))
                poll_seconds = float(payload.get("poll_seconds", 0.5))
                stable_seconds = float(payload.get("stable_seconds", 1.2))
            except (KeyError, TypeError, ValueError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": [f"Invalid tap payload: {exc}"]})
                return
            if x < 0 or y < 0 or wait_seconds < 0 or min_wait_seconds < 0 or max_wait_seconds < 0 or poll_seconds < 0 or stable_seconds < 0:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["Coordinates and wait seconds must be non-negative."]})
                return
            if auto_wait and min_wait_seconds > max_wait_seconds:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["Minimum wait seconds cannot exceed maximum wait seconds."]})
                return

            tap_result = api.tap(x, y, adb_path=config.adb_path, serial=config.serial, execute=True)
            if not tap_result.ok:
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "messages": [f"tap failed with exit {tap_result.returncode}: {tap_result.stderr}"]},
                )
                return
            screenshot_path = _next_capture_path(config.screenshot_path, capture_state)
            if auto_wait:
                elapsed_wait, screenshot_result = _capture_until_stable(
                    current_path=Path(capture_state["current_path"]),
                    out_path=screenshot_path,
                    min_wait_seconds=min_wait_seconds,
                    max_wait_seconds=max_wait_seconds,
                    poll_seconds=poll_seconds,
                    stable_seconds=stable_seconds,
                    adb_path=config.adb_path,
                    serial=config.serial,
                )
            else:
                if wait_seconds:
                    time.sleep(wait_seconds)
                screenshot_result = api.screenshot(screenshot_path, adb_path=config.adb_path, serial=config.serial)
                elapsed_wait = wait_seconds
            if not screenshot_result.ok:
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "messages": [f"screencap failed with exit {screenshot_result.returncode}: {screenshot_result.stderr}"]},
                )
                return
            capture_state["current_path"] = screenshot_path

            steps = [{"type": "tap", "x": x, "y": y, "label": label}]
            rounded_wait = round(elapsed_wait, 2)
            if rounded_wait:
                steps.append({"type": "wait", "seconds": rounded_wait})
            steps.append({"type": "screenshot", "out": screenshot_path.as_posix()})
            payload = _screenshot_payload(screenshot_path, steps=steps)
            payload["wait_seconds"] = rounded_wait
            payload["auto_wait"] = auto_wait
            self._write_json(HTTPStatus.OK, payload)

        def _run_script(self) -> None:
            payload = self._read_json_payload()
            if payload is None:
                return
            yaml_text = payload.get("yaml")
            execute_taps = bool(payload.get("execute_taps", False))
            if execute_taps and not config.allow_device_input:
                self._write_json(HTTPStatus.FORBIDDEN, {"ok": False, "messages": ["Device input is not enabled for this recorder."]})
                return
            if not isinstance(yaml_text, str) or not yaml_text.strip():
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": ["YAML content is required."]})
                return
            try:
                config.script_path.parent.mkdir(parents=True, exist_ok=True)
                config.script_path.write_text(yaml_text, encoding="utf-8")
            except OSError as exc:
                self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "messages": [f"Cannot write script: {exc}"]})
                return

            try:
                summary = agent_run_script(
                    config.script_path,
                    artifact_root=_default_artifact_root(config.script_path),
                    execute_taps=execute_taps,
                    allow_device_input=config.allow_device_input,
                    intent="recorder UI test run",
                    adb_path=config.adb_path,
                    serial=config.serial,
                )
            except (RunnerError, SafetyError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": _expand_adb_messages(str(exc), config)})
                return

            messages = format_report(summary.validation)
            messages.append("Real taps were sent." if not summary.report.dry_run_taps else "Tap steps were dry-run.")
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "status": summary.report.status,
                    "messages": messages,
                    "report_path": summary.report_path.as_posix(),
                    "audit_path": summary.audit_path.as_posix(),
                    "executed": summary.report.executed,
                    "dry_run_taps": summary.report.dry_run_taps,
                },
            )

        def _read_json_payload(self) -> dict | None:
            if self.path not in {"/api/script", "/api/capture", "/api/tap-capture", "/api/run"}:
                self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "messages": ["Not found."]})
                return None
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_POST_BYTES:
                self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "messages": ["Script is too large."]})
                return None
            try:
                raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
                return json.loads(raw_body)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "messages": [f"Invalid request: {exc}"]})
                return None

        def log_message(self, format: str, *args) -> None:
            return

        def _write_text(self, status: HTTPStatus, content: str, content_type: str) -> None:
            data = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _write_json(self, status: HTTPStatus, payload: dict) -> None:
            self._write_text(status, json.dumps(payload, sort_keys=True), "application/json; charset=utf-8")

    return RecorderHandler


def _capture_until_stable(
    current_path: Path,
    out_path: Path,
    min_wait_seconds: float,
    max_wait_seconds: float,
    poll_seconds: float,
    stable_seconds: float,
    adb_path: str | None = None,
    serial: str | None = None,
) -> tuple[float, AdbResult]:
    try:
        before = current_path.read_bytes()
    except OSError:
        before = b""
    started = time.monotonic()
    if min_wait_seconds:
        time.sleep(min_wait_seconds)
    last_result = api.screenshot(out_path, adb_path=adb_path, serial=serial)
    if not last_result.ok:
        return time.monotonic() - started, last_result
    last_bytes = _read_bytes(out_path)
    stable_since = time.monotonic()
    while True:
        elapsed = time.monotonic() - started
        changed_from_start = last_bytes != before
        stable_elapsed = time.monotonic() - stable_since
        if (changed_from_start and stable_elapsed >= stable_seconds) or elapsed >= max_wait_seconds:
            return elapsed, last_result
        if poll_seconds:
            time.sleep(min(poll_seconds, max_wait_seconds - elapsed))
        last_result = api.screenshot(out_path, adb_path=adb_path, serial=serial)
        if not last_result.ok:
            return time.monotonic() - started, last_result
        current_bytes = _read_bytes(out_path)
        if current_bytes != last_bytes:
            last_bytes = current_bytes
            stable_since = time.monotonic()


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _default_artifact_root(script_path: Path) -> Path:
    if script_path.parent.name == "scripts":
        return script_path.parent.parent / "artifacts"
    return Path("artifacts")


def _expand_adb_messages(message: str, config: RecorderServerConfig) -> list[str]:
    messages = [message]
    if config.serial or "more than one device/emulator" not in message:
        return messages
    report = api.doctor(adb_path=config.adb_path)
    serial_line = next((line for line in report.lines if line.startswith("Connected devices: ")), "")
    serials = [item.strip() for item in serial_line.removeprefix("Connected devices: ").split(",") if item.strip()]
    if serials:
        messages.append("ADB found multiple devices. Restart record-ui with one of these serial values:")
        messages.extend(f"--serial {serial}" for serial in serials)
    else:
        messages.append("ADB found multiple devices. Run `py -m autoplay doctor` and restart record-ui with --serial.")
    return messages


def _next_capture_path(base_path: Path, state: dict[str, object]) -> Path:
    state["index"] = int(state["index"]) + 1
    return base_path.with_name(f"{base_path.stem}-{int(state['index']):03d}{base_path.suffix or '.png'}")


def _screenshot_payload(screenshot_path: Path, steps: list[dict]) -> dict:
    image_bytes = screenshot_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return {
        "ok": True,
        "status": "captured",
        "screenshot_path": screenshot_path.as_posix(),
        "image_data_url": f"data:image/png;base64,{encoded}",
        "steps": steps,
        "messages": [f"Captured {screenshot_path}."],
    }
