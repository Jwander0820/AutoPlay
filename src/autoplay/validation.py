from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .script import (
    AutoplayScript,
    CheckpointExistsStep,
    CheckpointMatchStep,
    ScreenshotStep,
    ScriptError,
    TapStep,
    WaitStep,
    load_script,
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def validate_script_file(path: str | Path) -> ValidationReport:
    try:
        script = load_script(path)
    except ScriptError as exc:
        return ValidationReport([ValidationIssue("error", str(exc))])
    return validate_script(script)


def validate_script(script: AutoplayScript) -> ValidationReport:
    issues: list[ValidationIssue] = []
    screenshot_outputs: set[Path] = set()

    for index, step in enumerate(script.steps, start=1):
        if isinstance(step, WaitStep):
            if step.seconds > 60:
                issues.append(ValidationIssue("warning", f"step {index}: wait longer than 60 seconds."))
            continue

        if isinstance(step, TapStep):
            if not step.label:
                issues.append(ValidationIssue("warning", f"step {index}: tap has no label."))
            continue

        if isinstance(step, ScreenshotStep):
            _warn_if_non_png(issues, index, step.out)
            _warn_if_outside_script_dir(issues, index, script.source_path.parent, step.out)
            screenshot_outputs.add(step.out)
            continue

        if isinstance(step, CheckpointExistsStep):
            _warn_if_outside_script_dir(issues, index, script.source_path.parent, step.path)
            if step.path not in screenshot_outputs and not step.path.exists():
                issues.append(
                    ValidationIssue(
                        "error",
                        f"step {index}: checkpoint path is neither created by an earlier screenshot nor present on disk: {step.path}",
                    )
                )
            continue

        if isinstance(step, CheckpointMatchStep):
            _warn_if_outside_script_dir(issues, index, script.source_path.parent, step.source)
            _warn_if_outside_script_dir(issues, index, script.source_path.parent, step.template)
            if step.source not in screenshot_outputs and not step.source.exists():
                issues.append(
                    ValidationIssue(
                        "error",
                        f"step {index}: match source is neither created by an earlier screenshot nor present on disk: {step.source}",
                    )
                )
            if not step.template.exists():
                issues.append(ValidationIssue("error", f"step {index}: template file does not exist: {step.template}"))
            _warn_if_non_png(issues, index, step.source)
            _warn_if_non_png(issues, index, step.template)
            continue

    return ValidationReport(issues)


def format_report(report: ValidationReport) -> list[str]:
    if not report.issues:
        return ["OK: script passed validation."]
    lines: list[str] = []
    for issue in report.issues:
        lines.append(f"{issue.severity.upper()}: {issue.message}")
    if report.ok:
        lines.append("OK: script has warnings but no errors.")
    return lines


def _warn_if_non_png(issues: list[ValidationIssue], index: int, path: Path) -> None:
    if path.suffix.lower() != ".png":
        issues.append(ValidationIssue("warning", f"step {index}: screenshot output is not a .png file."))


def _warn_if_outside_script_dir(issues: list[ValidationIssue], index: int, base_dir: Path, path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(base_dir.resolve(strict=False))
    except ValueError:
        issues.append(ValidationIssue("warning", f"step {index}: path is outside the script directory: {path}"))
