from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adb import AdbResult
from .agent_tools import AgentPolicy, AgentSession, SafetyError
from .doctor import DoctorReport
from .image_match import MatchResult
from .ai_script_drafts import DraftScriptResult
from .local_config import LocalConfig, load_local_config
from .runner import RunnerReport
from .script import Region
from .ai_schemas import SUPPORTED_TOOLS
from .validation import ValidationReport


@dataclass(frozen=True)
class AiBridgeConfig:
    artifact_root: Path = Path("artifacts")
    audit_path: Path | None = None
    step_budget: int = 20
    allow_device_input: bool = False
    device_input_code: str | None = None
    script_root: Path = Path("scripts")
    adb_path: str | None = None
    serial: str | None = None


class AiBridge:
    def __init__(self, config: AiBridgeConfig | None = None):
        self.config = config or AiBridgeConfig()
        audit_path = self.config.audit_path or self.config.artifact_root / "agent" / "ai-bridge.jsonl"
        policy = AgentPolicy(
            artifact_root=self.config.artifact_root,
            audit_path=audit_path,
            step_budget=self.config.step_budget,
            allow_device_input=self.config.allow_device_input,
            script_root=self.config.script_root,
        )
        self.session = AgentSession(policy=policy, adb_path=self.config.adb_path, serial=self.config.serial)

    @classmethod
    def from_local_config(cls, local_config: LocalConfig | None = None, **overrides: Any) -> "AiBridge":
        local = local_config or load_local_config()
        config = AiBridgeConfig(
            artifact_root=Path(overrides.get("artifact_root", "artifacts")),
            audit_path=_optional_path(overrides.get("audit_path")),
            step_budget=int(overrides.get("step_budget", 20)),
            allow_device_input=bool(overrides.get("allow_device_input", False)),
            device_input_code=overrides.get("device_input_code"),
            script_root=Path(overrides.get("script_root", "scripts")),
            adb_path=overrides.get("adb_path") or local.adb_path,
            serial=overrides.get("serial") or local.serial,
        )
        return cls(config)

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            tool, args = _parse_request(request)
            self._require_device_input_code(tool, args)
            args = _strip_bridge_only_args(args)
            result = self._dispatch(tool, args)
            return {
                "ok": _result_ok(result),
                "tool": tool,
                "result": _result_to_dict(result),
                "messages": _result_messages(result),
                "steps_remaining": self.session.steps_remaining,
            }
        except SafetyError as exc:
            return _error_response(request, exc, blocked=True, steps_remaining=self.session.steps_remaining)
        except Exception as exc:
            return _error_response(request, exc, steps_remaining=self.session.steps_remaining)

    def _dispatch(self, tool: str, args: dict[str, Any]):
        if tool == "doctor":
            return self.session.doctor()
        if tool == "screenshot":
            return self.session.screenshot(args.get("out") or self.config.artifact_root / "ai" / "current.png")
        if tool == "match":
            return self.session.match(
                _required(args, "source"),
                _required(args, "template"),
                threshold=float(args.get("threshold", 0.95)),
                tolerance=int(args.get("tolerance", 0)),
                region=_optional_region(args.get("region")),
            )
        if tool == "tap":
            return self.session.tap(
                int(_required(args, "x")),
                int(_required(args, "y")),
                label=str(args.get("label") or "ai tap"),
                execute=bool(args.get("execute", False)),
            )
        if tool == "swipe":
            return self.session.swipe(
                int(_required(args, "x1")),
                int(_required(args, "y1")),
                int(_required(args, "x2")),
                int(_required(args, "y2")),
                label=str(args.get("label") or "ai swipe"),
                duration_ms=int(args.get("duration_ms", 300)),
                execute=bool(args.get("execute", False)),
            )
        if tool == "drag":
            return self.session.drag(
                int(_required(args, "x1")),
                int(_required(args, "y1")),
                int(_required(args, "x2")),
                int(_required(args, "y2")),
                label=str(args.get("label") or "ai drag"),
                duration_ms=int(args.get("duration_ms", 700)),
                execute=bool(args.get("execute", False)),
            )
        if tool == "scroll":
            return self.session.scroll(
                str(_required(args, "direction")),
                label=str(args.get("label") or "ai scroll"),
                distance=_optional_int(args.get("distance")),
                duration_ms=int(args.get("duration_ms", 400)),
                execute=bool(args.get("execute", False)),
            )
        if tool == "back":
            return self.session.back(label=str(args.get("label") or "ai back"), execute=bool(args.get("execute", False)))
        if tool == "validate":
            return self.session.validate(_required(args, "script"))
        if tool == "draft_script":
            return self.session.draft_script(
                _required(args, "script"),
                steps=args.get("steps"),
                yaml_text=args.get("yaml"),
                profile=args.get("profile"),
                overwrite=bool(args.get("overwrite", False)),
            )
        if tool == "run_script":
            report_out = args.get("report_out") or self.config.artifact_root / "ai" / "run-script-report.json"
            return self.session.run(
                _required(args, "script"),
                execute_taps=bool(args.get("execute", args.get("execute_taps", False))),
                report_out=report_out,
                intent=str(args.get("intent") or "local ai requested script run"),
            )
        raise ValueError(f"Unknown AI tool: {tool}. Supported tools: {', '.join(SUPPORTED_TOOLS)}")

    def _require_device_input_code(self, tool: str, args: dict[str, Any]) -> None:
        if not self.config.allow_device_input or not self.config.device_input_code:
            return
        if not _requests_real_device_input(tool, args):
            return
        provided = args.get("device_input_code")
        if not isinstance(provided, str) or provided != self.config.device_input_code:
            raise SafetyError("Real device input requires the current device_input_code.")


def _parse_request(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(request, dict):
        raise ValueError("AI tool request must be a JSON object.")
    tool = request.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("AI tool request requires a non-empty 'tool'.")
    args = request.get("args", {})
    if not isinstance(args, dict):
        raise ValueError("AI tool request 'args' must be an object.")
    return tool.strip(), args


def _requests_real_device_input(tool: str, args: dict[str, Any]) -> bool:
    if tool in {"tap", "swipe", "drag", "scroll", "back"}:
        return bool(args.get("execute", False))
    if tool == "run_script":
        return bool(args.get("execute", args.get("execute_taps", False)))
    return False


def _strip_bridge_only_args(args: dict[str, Any]) -> dict[str, Any]:
    if "device_input_code" not in args:
        return args
    stripped = dict(args)
    stripped.pop("device_input_code", None)
    return stripped


def _required(args: dict[str, Any], name: str) -> Any:
    if name not in args:
        raise ValueError(f"Missing required arg: {name}")
    return args[name]


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_path(value: Any) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _optional_region(value: Any) -> Region | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("region must contain exactly four integers: x, y, width, height.")
    x, y, width, height = (int(part) for part in value)
    return Region(x=x, y=y, width=width, height=height)


def _result_ok(result: Any) -> bool:
    if isinstance(result, (AdbResult, DoctorReport, ValidationReport, DraftScriptResult)):
        return result.ok
    if isinstance(result, MatchResult):
        return result.matched
    if isinstance(result, RunnerReport):
        return result.status == "ok"
    return True


def _result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, AdbResult):
        return {
            "ok": result.ok,
            "command": result.command,
            "returncode": result.returncode,
            "stderr": result.stderr,
            "stdout_bytes": len(result.stdout),
            "timed_out": result.timed_out,
            "dry_run": result.dry_run,
        }
    if isinstance(result, DoctorReport):
        return {"ok": result.ok, "lines": result.lines}
    if isinstance(result, MatchResult):
        return {"matched": result.matched, "score": result.score, "x": result.x, "y": result.y}
    if isinstance(result, ValidationReport):
        return {
            "ok": result.ok,
            "issues": [{"severity": issue.severity, "message": issue.message} for issue in result.issues],
        }
    if isinstance(result, DraftScriptResult):
        return result.to_dict()
    if isinstance(result, RunnerReport):
        return result.to_dict()
    return {}


def _result_messages(result: Any) -> list[str]:
    if isinstance(result, DoctorReport):
        return result.lines
    if isinstance(result, ValidationReport):
        return [f"{issue.severity}: {issue.message}" for issue in result.issues]
    if isinstance(result, DraftScriptResult):
        return [f"wrote {result.script_path}", *[f"{issue.severity}: {issue.message}" for issue in result.validation.issues]]
    if isinstance(result, RunnerReport):
        return result.executed
    if isinstance(result, AdbResult) and result.stderr:
        return [result.stderr]
    return []


def _error_response(request: Any, exc: Exception, blocked: bool = False, steps_remaining: int = 0) -> dict[str, Any]:
    tool = request.get("tool") if isinstance(request, dict) else None
    return {
        "ok": False,
        "tool": tool if isinstance(tool, str) else None,
        "result": {},
        "messages": [str(exc)],
        "blocked": blocked,
        "steps_remaining": steps_remaining,
    }
