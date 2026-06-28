from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel

from src.config import load_config
from src.preferences import clear_vote, load_preferences, load_profile, set_vote
from src.storage import list_bulletin_dates, load_bulletin

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _safe_url(url: str) -> str:
    if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
        return url
    return "#"


config: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global config
    config = load_config()
    STATIC_DIR.mkdir(exist_ok=True)
    from src import scheduler
    scheduler.start(config)
    yield
    from src import scheduler
    scheduler.stop()


app = FastAPI(title="Oasis Reader", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["safe_url"] = _safe_url


# ── HTML shell ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = None):
    return templates.TemplateResponse(
        "bulletin.html.j2",
        {"request": request, "initial_date": date or ""},
    )


# ── JSON API ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/bulletins/dates")
async def get_dates():
    data_dir = config["storage"]["data_dir"]
    return {"dates": list_bulletin_dates(data_dir)}


@app.get("/api/bulletins/{date}")
async def get_bulletin(date: str):
    data_dir = config["storage"]["data_dir"]
    bulletin = load_bulletin(data_dir, date)
    if not bulletin["generated_at"]:
        raise HTTPException(status_code=404, detail=f"No bulletin for {date}")

    items = sorted(
        bulletin["items"],
        key=lambda x: (x.get("recommendation_score", -1), x.get("timestamp", "")),
        reverse=True,
    )
    return {**bulletin, "items": items}


@app.get("/api/models")
async def get_models():
    llm = config["llm"]
    models = llm.get("models") or [llm["model"]]
    return {"models": models, "current": llm["model"]}


@app.get("/api/preferences")
async def get_preferences():
    data_dir = config["storage"]["data_dir"]
    return load_preferences(data_dir)


class VoteRequest(BaseModel):
    item_id: str
    vote: str


@app.post("/api/preferences")
async def post_preference(body: VoteRequest):
    if body.vote not in ("like", "dislike"):
        raise HTTPException(status_code=422, detail="vote must be 'like' or 'dislike'")
    data_dir = config["storage"]["data_dir"]
    set_vote(data_dir, body.item_id, body.vote)
    prefs = load_preferences(data_dir)
    return {"ok": True, "preferences_count": len(prefs["votes"])}


@app.delete("/api/preferences/{item_id}")
async def delete_preference(item_id: str):
    data_dir = config["storage"]["data_dir"]
    clear_vote(data_dir, item_id)
    return {"ok": True}


@app.get("/api/profile")
async def get_profile():
    data_dir = config["storage"]["data_dir"]
    return load_profile(data_dir)


@app.get("/api/status")
async def status():
    from src.pipeline import _lock
    return {"running": _lock.locked()}


@app.get("/api/progress")
async def get_progress():
    from src.summarizer import progress
    return progress


class RefreshRequest(BaseModel):
    model: str = None


@app.post("/api/refresh", status_code=202)
async def refresh(background_tasks: BackgroundTasks, body: RefreshRequest = RefreshRequest()):
    from src.pipeline import _lock
    if _lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline already running")

    model = body.model
    if model:
        allowed = config["llm"].get("models") or [config["llm"]["model"]]
        if model not in allowed:
            raise HTTPException(status_code=422, detail=f"Unknown model: {model}")

    background_tasks.add_task(_run_with_lock, model)
    return {"started": True}


async def _run_with_lock(model: str = None):
    from src.pipeline import try_run_pipeline
    await try_run_pipeline(config, model)
