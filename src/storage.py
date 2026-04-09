import json
from datetime import date, datetime, timedelta
from pathlib import Path


def save_bulletin(items: list[dict], data_dir: str, retention_days: int = 7) -> Path:
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


def load_bulletin(data_dir: str, target_date: str = None) -> dict:
    if target_date is None:
        target_date = date.today().isoformat()
    path = Path(data_dir) / "bulletins" / f"{target_date}.json"
    if not path.exists():
        return {"date": target_date, "generated_at": "", "items": []}
    return json.loads(path.read_text())


def _cleanup_old(bulletins_dir: Path, retention_days: int):
    cutoff = date.today() - timedelta(days=retention_days)
    for f in bulletins_dir.glob("*.json"):
        try:
            file_date = date.fromisoformat(f.stem)
            if file_date < cutoff:
                f.unlink()
        except ValueError:
            continue
