import json
import os
from datetime import datetime
from pathlib import Path


def _prefs_path(data_dir: str) -> Path:
    return Path(data_dir) / "preferences.json"


def _profile_path(data_dir: str) -> Path:
    return Path(data_dir) / "profile.json"


def _atomic_write(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def load_preferences(data_dir: str) -> dict:
    path = _prefs_path(data_dir)
    if not path.exists():
        return {"votes": {}, "updated_at": None}
    return json.loads(path.read_text())


def set_vote(data_dir: str, item_id: str, vote: str):
    prefs = load_preferences(data_dir)
    prefs["votes"][item_id] = vote
    prefs["updated_at"] = datetime.now().isoformat()
    _atomic_write(_prefs_path(data_dir), prefs)


def clear_vote(data_dir: str, item_id: str):
    prefs = load_preferences(data_dir)
    prefs["votes"].pop(item_id, None)
    prefs["updated_at"] = datetime.now().isoformat()
    _atomic_write(_prefs_path(data_dir), prefs)


def load_profile(data_dir: str) -> dict:
    path = _profile_path(data_dir)
    if not path.exists():
        return {"summary": None, "updated_at": None, "seed_ids": [], "model": None}
    return json.loads(path.read_text())


def save_profile(data_dir: str, summary: str, seed_ids: list[str], model: str):
    data = {
        "summary": summary,
        "updated_at": datetime.now().isoformat(),
        "seed_ids": seed_ids,
        "model": model,
    }
    _atomic_write(_profile_path(data_dir), data)
