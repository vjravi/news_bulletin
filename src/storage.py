import json
from datetime import date, datetime, timedelta
from pathlib import Path


def save_bulletin(items: list[dict], data_dir: str, retention_days: int = 30) -> Path:
    today = date.today().isoformat()
    bulletins_dir = Path(data_dir) / "bulletins"
    bulletins_dir.mkdir(parents=True, exist_ok=True)

    bulletin = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "items": items,
    }
    path = bulletins_dir / f"{today}.json"
    path.write_text(json.dumps(bulletin, indent=2, ensure_ascii=False))

    _cleanup_old(bulletins_dir, retention_days)
    return path


def list_bulletin_dates(data_dir: str) -> list[str]:
    bulletins_dir = Path(data_dir) / "bulletins"
    if not bulletins_dir.exists():
        return []
    dates = []
    for f in sorted(bulletins_dir.glob("*.json"), reverse=True):
        try:
            date.fromisoformat(f.stem)
            dates.append(f.stem)
        except ValueError:
            continue
    return dates


def load_bulletin(data_dir: str, target_date: str = None) -> dict:
    if target_date is None:
        target_date = date.today().isoformat()
    path = Path(data_dir) / "bulletins" / f"{target_date}.json"
    if not path.exists():
        return {"date": target_date, "generated_at": "", "items": []}
    return json.loads(path.read_text())


def update_bulletin_scores(data_dir: str, target_date: str, scores: dict):
    """Merge recommendation scores into an existing bulletin JSON (atomic write)."""
    import os
    path = Path(data_dir) / "bulletins" / f"{target_date}.json"
    if not path.exists():
        return
    bulletin = json.loads(path.read_text())
    for item in bulletin["items"]:
        if item["id"] in scores:
            s = scores[item["id"]]
            item["recommendation_score"] = s["recommendation_score"]
            item["recommendation_reason"] = s.get("recommendation_reason")
            item["scored_at"] = s["scored_at"]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(bulletin, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def find_items_by_ids(data_dir: str, ids: list[str]) -> list[dict]:
    """Scan bulletins newest-first and return items matching any of the given IDs."""
    target = set(ids)
    found = {}
    for d in list_bulletin_dates(data_dir):
        if not target - set(found.keys()):
            break
        bulletin = load_bulletin(data_dir, d)
        for item in bulletin.get("items", []):
            if item["id"] in target and item["id"] not in found:
                found[item["id"]] = item
    return list(found.values())


def _cleanup_old(bulletins_dir: Path, retention_days: int):
    cutoff = date.today() - timedelta(days=retention_days)
    for f in bulletins_dir.glob("*.json"):
        try:
            file_date = date.fromisoformat(f.stem)
            if file_date < cutoff:
                f.unlink()
        except ValueError:
            continue
