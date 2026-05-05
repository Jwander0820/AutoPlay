from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmulatorProfile:
    id: str
    label: str
    adb_candidates: tuple[str, ...] = ()
    connect_targets: tuple[str, ...] = ()
    window_titles: tuple[str, ...] = ()


LDPLAYER = EmulatorProfile(
    id="ldplayer",
    label="LDPlayer / LeiDian",
    adb_candidates=(
        r"C:\LDPlayer\LDPlayer9\adb.exe",
        r"C:\Program Files\LDPlayer\LDPlayer9\adb.exe",
        r"C:\leidian\LDPlayer9\adb.exe",
        r"D:\LDPlayer\LDPlayer9\adb.exe",
    ),
    connect_targets=("127.0.0.1:5555", "127.0.0.1:5557", "127.0.0.1:5559"),
    window_titles=("LDPlayer", "LeiDian", "雷電"),
)

BLUESTACKS = EmulatorProfile(
    id="bluestacks",
    label="BlueStacks",
    adb_candidates=(r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",),
    connect_targets=(),
    window_titles=("BlueStacks",),
)

GENERIC_ADB = EmulatorProfile(
    id="generic",
    label="Generic Android ADB",
    adb_candidates=(),
    connect_targets=(),
    window_titles=(),
)

PROFILES = (LDPLAYER, BLUESTACKS, GENERIC_ADB)
PROFILE_BY_ID = {profile.id: profile for profile in PROFILES}


def get_profile(profile_id: str | None) -> EmulatorProfile:
    if profile_id and profile_id in PROFILE_BY_ID:
        return PROFILE_BY_ID[profile_id]
    return LDPLAYER


def profile_label_to_id(label: str) -> str:
    for profile in PROFILES:
        if profile.label == label:
            return profile.id
    return LDPLAYER.id


def profile_id_to_label(profile_id: str | None) -> str:
    return get_profile(profile_id).label


def first_existing_adb_candidate(profile: EmulatorProfile) -> str | None:
    from .paths import path_exists_for_host

    for candidate in profile.adb_candidates:
        if path_exists_for_host(candidate):
            return candidate
    return None
