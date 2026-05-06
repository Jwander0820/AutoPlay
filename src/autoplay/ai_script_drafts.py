from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .script import ScriptError
from .validation import ValidationReport, validate_script_file


@dataclass(frozen=True)
class DraftScriptResult:
    script_path: Path
    validation: ValidationReport
    step_count: int
    overwritten: bool

    @property
    def ok(self) -> bool:
        return self.validation.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "script_path": str(self.script_path),
            "step_count": self.step_count,
            "overwritten": self.overwritten,
            "issues": [{"severity": issue.severity, "message": issue.message} for issue in self.validation.issues],
        }


def draft_script_file(
    script_path: str | Path,
    steps: list[dict[str, Any]] | None = None,
    yaml_text: str | None = None,
    profile: dict[str, Any] | None = None,
    overwrite: bool = False,
    script_root: str | Path = "scripts",
) -> DraftScriptResult:
    out_path = _require_script_path(Path(script_path), Path(script_root))
    if out_path.exists() and not overwrite:
        raise ScriptError(f"Script already exists: {out_path}. Pass overwrite=true to replace it.")
    data = _coerce_script_data(steps=steps, yaml_text=yaml_text, profile=profile)
    overwritten = out_path.exists()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    validation = validate_script_file(out_path)
    return DraftScriptResult(script_path=out_path, validation=validation, step_count=len(data["steps"]), overwritten=overwritten)


def _require_script_path(path: Path, script_root: Path) -> Path:
    if path.is_absolute():
        candidate = path
    else:
        candidate = Path.cwd() / path
    root = script_root if script_root.is_absolute() else Path.cwd() / script_root
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise ScriptError(f"AI script drafts must be written under {script_root}.") from exc
    if candidate.suffix.lower() not in {".yml", ".yaml"}:
        raise ScriptError("AI script drafts must use a .yml or .yaml extension.")
    return candidate


def _coerce_script_data(
    steps: list[dict[str, Any]] | None,
    yaml_text: str | None,
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    if steps is not None and yaml_text is not None:
        raise ScriptError("Provide either steps or yaml, not both.")
    if yaml_text is not None:
        data = _load_yaml_mapping(yaml_text)
    else:
        if not isinstance(steps, list) or not steps:
            raise ScriptError("draft_script requires a non-empty steps list or yaml text.")
        data = {"steps": steps}
        if profile:
            data["profile"] = profile
    _reject_private_profile(data)
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ScriptError("Draft script must contain a non-empty steps list.")
    return data


def _load_yaml_mapping(yaml_text: str) -> dict[str, Any]:
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ScriptError("yaml must be a non-empty string.")
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ScriptError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ScriptError("Draft YAML must be a mapping.")
    return data


def _reject_private_profile(data: dict[str, Any]) -> None:
    profile = data.get("profile")
    if profile is None:
        return
    if not isinstance(profile, dict):
        raise ScriptError("profile must be a mapping.")
    if "adb_path" in profile:
        raise ScriptError("AI script drafts must not write profile.adb_path; use ignored local config instead.")
