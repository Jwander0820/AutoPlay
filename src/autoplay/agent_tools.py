from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import api
from .adb import AdbResult
from .doctor import DoctorReport
from .image_match import MatchResult
from .runner import RunnerReport
from .script import BackStep, DragStep, Region, ScriptError, ScrollStep, SwipeStep, TapStep, load_script
from .validation import ValidationReport


class SafetyError(RuntimeError):
    pass


BLOCKED_INTENT_TERMS = (
    "purchase",
    "buy",
    "payment",
    "gacha",
    "summon",
    "trade",
    "sell",
    "delete",
    "chat",
    "pvp",
    "verification code",
    "otp",
    "password",
    "credential",
    "login",
    "anti-cheat",
    "root",
    "hook",
    "memory edit",
    "購買",
    "付款",
    "抽卡",
    "召喚",
    "交易",
    "販售",
    "刪除",
    "聊天",
    "對戰",
    "驗證碼",
    "密碼",
    "登入",
    "反作弊",
    "外掛",
)


@dataclass(frozen=True)
class AgentPolicy:
    step_budget: int = 20
    allow_device_input: bool = False
    require_artifacts: bool = True
    artifact_root: Path = Path("artifacts")
    audit_path: Path = Path("artifacts/agent/audit.jsonl")
    blocked_terms: tuple[str, ...] = BLOCKED_INTENT_TERMS


class AgentSession:
    def __init__(self, policy: AgentPolicy | None = None, adb_path: str | None = None, serial: str | None = None):
        self.policy = policy or AgentPolicy()
        self.adb_path = adb_path
        self.serial = serial
        self.steps_used = 0

    @property
    def steps_remaining(self) -> int:
        return max(self.policy.step_budget - self.steps_used, 0)

    def doctor(self) -> DoctorReport:
        return self._call("doctor", {}, lambda: api.doctor(adb_path=self.adb_path, serial=self.serial))

    def screenshot(self, out: str | Path) -> AdbResult:
        out_path = Path(out)
        metadata = {"out": str(out_path)}
        self._consume_step("screenshot", metadata)
        try:
            self._require_artifact_path(out_path, "screenshot output")
        except SafetyError as exc:
            return self._blocked("screenshot", metadata, str(exc))
        return self._call(
            "screenshot",
            metadata,
            lambda: api.screenshot(out_path, adb_path=self.adb_path, serial=self.serial),
            consume_step=False,
        )

    def tap(self, x: int, y: int, label: str, execute: bool = False) -> AdbResult:
        metadata = {"x": x, "y": y, "label": label, "execute": execute}
        self._consume_step("tap", metadata)
        try:
            self._assert_safe_text(label, "tap label")
        except SafetyError as exc:
            return self._blocked("tap", metadata, str(exc))
        if execute and not self.policy.allow_device_input:
            return self._blocked(
                "tap",
                metadata,
                "Real device input is blocked by this agent policy.",
            )
        will_execute = execute and self.policy.allow_device_input
        metadata["execute"] = will_execute
        return self._call(
            "tap",
            metadata,
            lambda: api.tap(x, y, adb_path=self.adb_path, serial=self.serial, execute=will_execute),
            consume_step=False,
        )

    def swipe(self, x1: int, y1: int, x2: int, y2: int, label: str, duration_ms: int = 300, execute: bool = False) -> AdbResult:
        metadata = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms, "label": label, "execute": execute}
        self._consume_step("swipe", metadata)
        try:
            self._assert_safe_text(label, "swipe label")
        except SafetyError as exc:
            return self._blocked("swipe", metadata, str(exc))
        if execute and not self.policy.allow_device_input:
            return self._blocked("swipe", metadata, "Real device input is blocked by this agent policy.")
        will_execute = execute and self.policy.allow_device_input
        metadata["execute"] = will_execute
        return self._call(
            "swipe",
            metadata,
            lambda: api.swipe(x1, y1, x2, y2, duration_ms=duration_ms, adb_path=self.adb_path, serial=self.serial, execute=will_execute),
            consume_step=False,
        )

    def drag(self, x1: int, y1: int, x2: int, y2: int, label: str, duration_ms: int = 700, execute: bool = False) -> AdbResult:
        metadata = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms, "label": label, "execute": execute}
        self._consume_step("drag", metadata)
        try:
            self._assert_safe_text(label, "drag label")
        except SafetyError as exc:
            return self._blocked("drag", metadata, str(exc))
        if execute and not self.policy.allow_device_input:
            return self._blocked("drag", metadata, "Real device input is blocked by this agent policy.")
        will_execute = execute and self.policy.allow_device_input
        metadata["execute"] = will_execute
        return self._call(
            "drag",
            metadata,
            lambda: api.drag(x1, y1, x2, y2, duration_ms=duration_ms, adb_path=self.adb_path, serial=self.serial, execute=will_execute),
            consume_step=False,
        )

    def scroll(self, direction: str, label: str, distance: int | None = None, duration_ms: int = 400, execute: bool = False) -> AdbResult:
        metadata = {"direction": direction, "distance": distance, "duration_ms": duration_ms, "label": label, "execute": execute}
        self._consume_step("scroll", metadata)
        try:
            self._assert_safe_text(label, "scroll label")
        except SafetyError as exc:
            return self._blocked("scroll", metadata, str(exc))
        if execute and not self.policy.allow_device_input:
            return self._blocked("scroll", metadata, "Real device input is blocked by this agent policy.")
        will_execute = execute and self.policy.allow_device_input
        metadata["execute"] = will_execute
        return self._call(
            "scroll",
            metadata,
            lambda: api.scroll(direction, distance=distance, duration_ms=duration_ms, adb_path=self.adb_path, serial=self.serial, execute=will_execute),
            consume_step=False,
        )

    def back(self, label: str, execute: bool = False) -> AdbResult:
        metadata = {"label": label, "execute": execute}
        self._consume_step("back", metadata)
        try:
            self._assert_safe_text(label, "back label")
        except SafetyError as exc:
            return self._blocked("back", metadata, str(exc))
        if execute and not self.policy.allow_device_input:
            return self._blocked("back", metadata, "Real device input is blocked by this agent policy.")
        will_execute = execute and self.policy.allow_device_input
        metadata["execute"] = will_execute
        return self._call(
            "back",
            metadata,
            lambda: api.back(adb_path=self.adb_path, serial=self.serial, execute=will_execute),
            consume_step=False,
        )

    def validate(self, script_path: str | Path) -> ValidationReport:
        return self._call("validate", {"script_path": str(script_path)}, lambda: api.validate(script_path))

    def run(self, script_path: str | Path, execute_taps: bool = False, report_out: str | Path | None = None, intent: str = "") -> RunnerReport:
        metadata = {"script_path": str(script_path), "execute_taps": execute_taps, "report_out": _optional_path(report_out), "intent": intent}
        self._consume_step("run", metadata)
        try:
            self._assert_safe_text(intent, "run intent")
            self._assert_script_safe(script_path)
            if report_out is not None:
                self._require_artifact_path(Path(report_out), "run report")
        except SafetyError as exc:
            return self._blocked("run", metadata, str(exc))
        if execute_taps and not self.policy.allow_device_input:
            return self._blocked(
                "run",
                metadata,
                "Real tap execution and gesture input is blocked by this agent policy.",
            )
        will_execute = execute_taps and self.policy.allow_device_input
        metadata["execute_taps"] = will_execute
        return self._call(
            "run",
            metadata,
            lambda: api.run(script_path, execute_taps=will_execute, report_out=report_out, adb_path=self.adb_path, serial=self.serial),
            consume_step=False,
        )

    def match(
        self,
        source: str | Path,
        template: str | Path,
        threshold: float = 0.95,
        tolerance: int = 0,
        region: Region | Sequence[int] | None = None,
    ) -> MatchResult:
        metadata = {
            "source": str(source),
            "template": str(template),
            "threshold": threshold,
            "tolerance": tolerance,
            "region": _region_to_metadata(region),
        }
        self._consume_step("match", metadata)
        try:
            self._require_artifact_path(Path(source), "match source")
            self._require_artifact_path(Path(template), "match template")
        except SafetyError as exc:
            return self._blocked("match", metadata, str(exc))
        return self._call(
            "match",
            metadata,
            lambda: api.match(source, template, threshold=threshold, tolerance=tolerance, region=region),
            consume_step=False,
        )

    def _call(self, tool: str, metadata: dict[str, Any], callback, consume_step: bool = True):
        if consume_step:
            self._consume_step(tool, metadata)
        try:
            result = callback()
        except Exception as exc:
            self._write_audit(tool, "error", metadata, error=str(exc))
            raise
        self._write_audit(tool, "ok", metadata, result=_result_to_metadata(result))
        return result

    def _blocked(self, tool: str, metadata: dict[str, Any], message: str):
        self._write_audit(tool, "blocked", metadata, error=message)
        raise SafetyError(message)

    def _consume_step(self, tool: str, metadata: dict[str, Any]) -> None:
        if self.steps_used >= self.policy.step_budget:
            self._write_audit(tool, "blocked", metadata, error="Agent step budget exhausted.")
            raise SafetyError("Agent step budget exhausted.")
        self.steps_used += 1

    def _require_artifact_path(self, path: Path, description: str) -> None:
        if not self.policy.require_artifacts:
            return
        if _is_relative_to(path, self.policy.artifact_root):
            return
        raise SafetyError(f"{description} must be under {self.policy.artifact_root}.")

    def _assert_safe_text(self, value: str | None, description: str) -> None:
        if not value:
            return
        lowered = value.lower()
        for term in self.policy.blocked_terms:
            if term.lower() in lowered:
                raise SafetyError(f"{description} contains blocked term: {term}")

    def _assert_script_safe(self, script_path: str | Path) -> None:
        try:
            script = load_script(script_path)
        except ScriptError:
            return
        for index, step in enumerate(script.steps, start=1):
            if isinstance(step, TapStep):
                self._assert_safe_text(step.label, f"tap label at step {index}")
            if isinstance(step, SwipeStep):
                self._assert_safe_text(step.label, f"swipe label at step {index}")
            if isinstance(step, DragStep):
                self._assert_safe_text(step.label, f"drag label at step {index}")
            if isinstance(step, ScrollStep):
                self._assert_safe_text(step.label, f"scroll label at step {index}")
            if isinstance(step, BackStep):
                self._assert_safe_text(step.label, f"back label at step {index}")

    def _write_audit(self, tool: str, status: str, metadata: dict[str, Any], result: dict[str, Any] | None = None, error: str | None = None) -> None:
        event = {
            "timestamp": _utc_now(),
            "tool": tool,
            "status": status,
            "steps_used": self.steps_used,
            "steps_remaining": self.steps_remaining,
            "metadata": metadata,
            "result": result or {},
            "error": error,
        }
        audit_path = self.policy.audit_path
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        if not audit_path.exists():
            audit_path.write_text("", encoding="utf-8")
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _optional_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


def _region_to_metadata(region: Region | Sequence[int] | None) -> list[int] | None:
    if region is None:
        return None
    if isinstance(region, Region):
        return [region.x, region.y, region.width, region.height]
    return list(region)


def _result_to_metadata(result: Any) -> dict[str, Any]:
    if isinstance(result, AdbResult):
        return {
            "ok": result.ok,
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "dry_run": result.dry_run,
            "stdout_bytes": len(result.stdout),
        }
    if isinstance(result, MatchResult):
        return {"matched": result.matched, "score": result.score, "x": result.x, "y": result.y}
    if isinstance(result, RunnerReport):
        return {"status": result.status, "dry_run_taps": result.dry_run_taps, "events": len(result.events)}
    if isinstance(result, ValidationReport):
        return {"ok": result.ok, "errors": len(result.errors), "warnings": len(result.warnings)}
    if isinstance(result, DoctorReport):
        return {"ok": result.ok}
    return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
