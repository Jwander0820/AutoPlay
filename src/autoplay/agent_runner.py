from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent_tools import AgentPolicy, AgentSession
from .runner import RunnerError, RunnerReport
from .validation import ValidationReport


@dataclass(frozen=True)
class AgentRunSummary:
    validation: ValidationReport
    report: RunnerReport
    report_path: Path
    audit_path: Path


def agent_run_script(
    script_path: str | Path,
    artifact_root: str | Path = "artifacts",
    report_out: str | Path | None = None,
    audit_out: str | Path | None = None,
    step_budget: int = 20,
    execute_taps: bool = False,
    allow_device_input: bool = False,
    intent: str = "daily task dry run",
    adb_path: str | None = None,
    serial: str | None = None,
) -> AgentRunSummary:
    script = Path(script_path)
    root = Path(artifact_root)
    report_path = Path(report_out) if report_out is not None else _default_report_path(script, root, execute_taps and allow_device_input)
    audit_path = Path(audit_out) if audit_out is not None else _default_audit_path(script, root)
    policy = AgentPolicy(
        step_budget=step_budget,
        allow_device_input=allow_device_input,
        artifact_root=root,
        audit_path=audit_path,
    )
    session = AgentSession(policy=policy, adb_path=adb_path, serial=serial)

    validation = session.validate(script)
    if not validation.ok:
        messages = "\n".join(issue.message for issue in validation.errors)
        raise RunnerError(f"Agent validation failed:\n{messages}")

    report = session.run(script, execute_taps=execute_taps, report_out=report_path, intent=intent)
    return AgentRunSummary(validation=validation, report=report, report_path=report_path, audit_path=audit_path)


def _default_report_path(script_path: Path, artifact_root: Path, real_taps: bool) -> Path:
    mode = "real" if real_taps else "dry-run"
    return artifact_root / "reports" / f"{script_path.stem}-agent-{mode}.json"


def _default_audit_path(script_path: Path, artifact_root: Path) -> Path:
    return artifact_root / "agent" / f"{script_path.stem}-audit.jsonl"
