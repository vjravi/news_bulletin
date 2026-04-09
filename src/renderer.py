from pathlib import Path
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _safe_url(url: str) -> str:
    if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
        return url
    return "#"


def render_bulletin(bulletin: dict, html_path: str) -> Path:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["safe_url"] = _safe_url
    template = env.get_template("bulletin.html.j2")

    html = template.render(
        date=bulletin["date"],
        generated_at=bulletin["generated_at"],
        items=bulletin["items"],
    )

    out = Path(html_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
