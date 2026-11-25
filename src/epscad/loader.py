from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping YAML at {target}")
    return data


def load_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping JSON at {target}")
    return data


def load_machine_profile(profile_id: str) -> dict[str, Any]:
    if profile_id not in {"scara_hotwire_eps", "scara_hotwire_teste"}:
        raise FileNotFoundError("Unknown machine profile: "+profile_id)
    # Explicit private profile used consistently by build, validation and publishing.
    override = os.environ.get("EPS_SCARA_PROFILE_FILE") if profile_id == "scara_hotwire_eps" else None
    target = Path(override).expanduser().resolve() if override else ROOT / "machine_profiles" / f"{profile_id}.yaml"
    if not target.exists():
        raise FileNotFoundError(f"Machine profile not found: {target}")
    profile = load_yaml(target)
    if profile.get("id") != profile_id:
        raise ValueError("Machine profile ID mismatch")
    return profile
