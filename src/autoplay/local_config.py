from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .emulator_profiles import LDPLAYER


LOCAL_CONFIG_PATH = Path("config") / "autoplay.local.json"


@dataclass(frozen=True)
class LocalConfig:
    emulator_profile: str = LDPLAYER.id
    adb_path: str | None = None
    serial: str | None = None
    connect_targets: tuple[str, ...] = LDPLAYER.connect_targets
    script_path: str = "scripts/ldplayer-test.yml"
    screenshot_path: str = "artifacts/manual/ldplayer-start.png"
    recorder_port: int = 0
    allow_device_input: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalConfig":
        config = cls()
        updates: dict[str, Any] = {}
        if isinstance(data.get("emulator_profile"), str):
            updates["emulator_profile"] = data["emulator_profile"]
        if isinstance(data.get("adb_path"), str):
            updates["adb_path"] = data["adb_path"]
        if isinstance(data.get("serial"), str):
            updates["serial"] = data["serial"]
        if isinstance(data.get("connect_targets"), list):
            targets = tuple(target for target in data["connect_targets"] if isinstance(target, str) and target.strip())
            if targets:
                updates["connect_targets"] = targets
        if isinstance(data.get("script_path"), str):
            updates["script_path"] = data["script_path"]
        if isinstance(data.get("screenshot_path"), str):
            updates["screenshot_path"] = data["screenshot_path"]
        if isinstance(data.get("recorder_port"), int) and data["recorder_port"] >= 0:
            updates["recorder_port"] = data["recorder_port"]
        if isinstance(data.get("allow_device_input"), bool):
            updates["allow_device_input"] = data["allow_device_input"]
        return replace(config, **updates)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "emulator_profile": self.emulator_profile,
            "connect_targets": list(self.connect_targets),
            "script_path": self.script_path,
            "screenshot_path": self.screenshot_path,
            "recorder_port": self.recorder_port,
            "allow_device_input": self.allow_device_input,
        }
        if self.adb_path:
            data["adb_path"] = self.adb_path
        if self.serial:
            data["serial"] = self.serial
        return data


def load_local_config(path: str | Path = LOCAL_CONFIG_PATH) -> LocalConfig:
    config_path = Path(path)
    if not config_path.exists():
        return LocalConfig()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return LocalConfig()
    return LocalConfig.from_dict(data)


def save_local_config(config: LocalConfig, path: str | Path = LOCAL_CONFIG_PATH) -> Path:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path
