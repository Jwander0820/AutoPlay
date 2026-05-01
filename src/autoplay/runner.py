from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adb import AdbClient, AdbResult
from .gestures import compile_scroll, swipe_metadata
from .image_match import ImageError, match_template_file
from .paths import resolve_adb_path
from .script import AutoplayScript, BackStep, CheckpointExistsStep, CheckpointMatchStep, DragStep, ScreenshotStep, ScrollStep, SwipeStep, TapStep, WaitStep, load_script
from .validation import validate_script


class RunnerError(RuntimeError):
    def __init__(self, message: str, report: RunnerReport | None = None):
        super().__init__(message)
        self.report = report


@dataclass
class RunEvent:
    index: int
    step_type: str
    status: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "step_type": self.step_type,
            "status": self.status,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class RunnerReport:
    executed: list[str] = field(default_factory=list)
    results: list[AdbResult] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: _utc_now())
    ended_at: str | None = None
    dry_run_taps: bool = False
    status: str = "running"
    error: str | None = None

    def finish(self, status: str = "ok", error: str | None = None) -> None:
        self.status = status
        self.error = error
        self.ended_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "dry_run_taps": self.dry_run_taps,
            "dry_run_device_input": self.dry_run_taps,
            "error": self.error,
            "executed": self.executed,
            "events": [event.to_dict() for event in self.events],
            "adb_results": [_adb_result_to_dict(result) for result in self.results],
        }


class Runner:
    def __init__(self, adb_client: AdbClient, dry_run_taps: bool = False):
        self.adb = adb_client
        self.dry_run_taps = dry_run_taps

    def run_script(self, script: AutoplayScript) -> RunnerReport:
        report = RunnerReport(dry_run_taps=self.dry_run_taps)
        for index, step in enumerate(script.steps, start=1):
            if isinstance(step, WaitStep):
                report.executed.append(f"{index}: wait {step.seconds}s")
                time.sleep(step.seconds)
                report.events.append(RunEvent(index=index, step_type="wait", status="ok", message=f"waited {step.seconds}s"))
                continue

            if isinstance(step, TapStep):
                result = self.adb.tap(step.x, step.y, dry_run=self.dry_run_taps)
                report.results.append(result)
                report.executed.append(f"{index}: tap {step.x},{step.y}")
                _raise_on_failed_adb(result, f"tap step {index}", report, index, "tap")
                report.events.append(
                    RunEvent(
                        index=index,
                        step_type="tap",
                        status="ok",
                        message=f"tap {step.x},{step.y}",
                        metadata={"x": step.x, "y": step.y, "dry_run": result.dry_run, "label": step.label},
                    )
                )
                continue

            if isinstance(step, SwipeStep):
                self._run_swipe_event(
                    report=report,
                    index=index,
                    step_type="swipe",
                    x1=step.x1,
                    y1=step.y1,
                    x2=step.x2,
                    y2=step.y2,
                    duration_ms=step.duration_ms,
                    label=step.label,
                    executed=f"{index}: swipe {step.x1},{step.y1} -> {step.x2},{step.y2}",
                    message=f"swipe {step.x1},{step.y1} -> {step.x2},{step.y2}",
                )
                continue

            if isinstance(step, DragStep):
                self._run_swipe_event(
                    report=report,
                    index=index,
                    step_type="drag",
                    x1=step.x1,
                    y1=step.y1,
                    x2=step.x2,
                    y2=step.y2,
                    duration_ms=step.duration_ms,
                    label=step.label,
                    executed=f"{index}: drag {step.x1},{step.y1} -> {step.x2},{step.y2}",
                    message=f"drag {step.x1},{step.y1} -> {step.x2},{step.y2}",
                )
                continue

            if isinstance(step, ScrollStep):
                x1, y1, x2, y2 = compile_scroll(step.direction, distance=step.distance)
                self._run_swipe_event(
                    report=report,
                    index=index,
                    step_type="scroll",
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    duration_ms=step.duration_ms,
                    label=step.label,
                    executed=f"{index}: scroll {step.direction}",
                    message=f"scroll {step.direction}",
                    extra_metadata={"direction": step.direction, "distance": step.distance},
                )
                continue

            if isinstance(step, BackStep):
                result = self.adb.back(dry_run=self.dry_run_taps)
                report.results.append(result)
                report.executed.append(f"{index}: back")
                _raise_on_failed_adb(result, f"back step {index}", report, index, "back")
                report.events.append(
                    RunEvent(
                        index=index,
                        step_type="back",
                        status="ok",
                        message="back",
                        metadata={"dry_run": result.dry_run, "label": step.label},
                    )
                )
                continue

            if isinstance(step, ScreenshotStep):
                result = self.adb.screencap(step.out)
                report.results.append(result)
                report.executed.append(f"{index}: screenshot {step.out}")
                _raise_on_failed_adb(result, f"screenshot step {index}", report, index, "screenshot")
                if not step.out.exists():
                    _fail(report, index, "screenshot", f"Screenshot step {index} did not create {step.out}")
                report.events.append(
                    RunEvent(index=index, step_type="screenshot", status="ok", message=f"wrote {step.out}", metadata={"out": str(step.out)})
                )
                continue

            if isinstance(step, CheckpointExistsStep):
                report.executed.append(f"{index}: checkpoint_exists {step.path}")
                if not step.path.exists():
                    _fail(report, index, "checkpoint_exists", f"Checkpoint step {index} failed; file does not exist: {step.path}")
                report.events.append(
                    RunEvent(
                        index=index,
                        step_type="checkpoint_exists",
                        status="ok",
                        message=f"found {step.path}",
                        metadata={"path": str(step.path)},
                    )
                )
                continue

            if isinstance(step, CheckpointMatchStep):
                report.executed.append(f"{index}: checkpoint_match {step.template}")
                try:
                    match = match_template_file(
                        step.source,
                        step.template,
                        threshold=step.threshold,
                        tolerance=step.tolerance,
                        region=step.region,
                    )
                except (OSError, ImageError) as exc:
                    _fail(report, index, "checkpoint_match", f"Checkpoint match step {index} failed: {exc}")
                if not match.matched:
                    _fail(
                        report,
                        index,
                        "checkpoint_match",
                        f"Checkpoint match step {index} failed; best score {match.score:.3f} below threshold {step.threshold:.3f}",
                        metadata={"score": match.score, "threshold": step.threshold, "x": match.x, "y": match.y},
                    )
                report.events.append(
                    RunEvent(
                        index=index,
                        step_type="checkpoint_match",
                        status="ok",
                        message=f"matched {step.template}",
                        metadata={
                            "source": str(step.source),
                            "template": str(step.template),
                            "score": match.score,
                            "threshold": step.threshold,
                            "x": match.x,
                            "y": match.y,
                        },
                    )
                )
                continue

            _fail(report, index, "unknown", f"Unsupported step at index {index}: {step!r}")
        report.finish()
        return report

    def _run_swipe_event(
        self,
        report: RunnerReport,
        index: int,
        step_type: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int,
        label: str | None,
        executed: str,
        message: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        result = self.adb.swipe(x1, y1, x2, y2, duration_ms, dry_run=self.dry_run_taps)
        report.results.append(result)
        report.executed.append(executed)
        _raise_on_failed_adb(result, f"{step_type} step {index}", report, index, step_type)
        metadata = swipe_metadata(x1, y1, x2, y2, duration_ms, result.dry_run, label)
        if extra_metadata:
            metadata.update(extra_metadata)
        report.events.append(RunEvent(index=index, step_type=step_type, status="ok", message=message, metadata=metadata))


def run_script_file(
    path: str | Path,
    dry_run_taps: bool = False,
    adb_path: str | None = None,
    serial: str | None = None,
) -> RunnerReport:
    script = load_script(path)
    validation = validate_script(script)
    if not validation.ok:
        messages = "\n".join(issue.message for issue in validation.errors)
        raise RunnerError(f"Script validation failed:\n{messages}")
    resolved_adb_path = resolve_adb_path(adb_path if adb_path is not None else script.profile.adb_path)
    adb_client = AdbClient(adb_path=resolved_adb_path, serial=serial if serial is not None else script.profile.serial)
    return Runner(adb_client, dry_run_taps=dry_run_taps).run_script(script)


def _raise_on_failed_adb(result: AdbResult, context: str, report: RunnerReport, index: int, step_type: str) -> None:
    if result.ok:
        return
    command = " ".join(result.command)
    message = f"ADB failed during {context} (exit {result.returncode}): {command}\n{result.stderr}"
    report.events.append(
        RunEvent(
            index=index,
            step_type=step_type,
            status="error",
            message=message,
            metadata={"command": result.command, "returncode": result.returncode, "timed_out": result.timed_out},
        )
    )
    report.finish(status="error", error=message)
    raise RunnerError(message, report=report)


def _fail(
    report: RunnerReport,
    index: int,
    step_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    report.events.append(RunEvent(index=index, step_type=step_type, status="error", message=message, metadata=metadata or {}))
    report.finish(status="error", error=message)
    raise RunnerError(message, report=report)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _adb_result_to_dict(result: AdbResult) -> dict[str, Any]:
    return {
        "command": result.command,
        "returncode": result.returncode,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
        "dry_run": result.dry_run,
        "stdout_bytes": len(result.stdout),
    }
