# News Summarizer — Oasis Reader

Aggregates AI/ML news from HackerNews, Reddit (r/LocalLLaMA), TLDR AI, and HuggingFace Papers, summarizes each item with a local LLM, and serves a personalized reading bulletin via FastAPI.

**Pipeline:** scrape (parallel) → summarize via Ollama → store JSON → refresh user profile → score items by relevance

**Serve:** FastAPI + vanilla JS frontend with a calendar archive and like/dislike voting

---

## Quickstart (local)

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally with the model pulled

```bash
ollama pull qwen3.5:9b-mlx-bf16
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start the server

```bash
uvicorn src.api:app --reload --port 8000
```

Open `http://localhost:8000`. The bulletin is empty until the pipeline runs.

### Run the pipeline (first time or on demand)

```bash
# Via the API
curl -X POST http://localhost:8000/api/refresh

# Or as a one-shot CLI
python -m src.graph
```

The scheduler will also run automatically at the time configured in `config.yaml` (`scheduler.daily_at`).

---

## Running with Docker

### Prerequisites

- Docker and Docker Compose
- [Ollama](https://ollama.com) running on your host machine

```bash
ollama pull qwen3.5:9b-mlx-bf16
```

### Start the service

```bash
docker compose up --build
```

Open `http://localhost:8000`.

The container connects to Ollama on your host via `host.docker.internal`.

---

## Configuration

Edit `config.yaml`:

```yaml
ollama:
  model: "qwen3.5:9b-mlx-bf16"
  base_url: "http://localhost:11434"

sources:
  hackernews:
    enabled: true
    max_items: 20
  reddit:
    enabled: true
    subreddits:
      - "LocalLLaMA"
    max_items: 15
  tldr:
    enabled: true
  papers:
    enabled: true
    filter: "date"         # date | week | month

storage:
  data_dir: "./data"
  retention_days: 30

scheduler:
  enabled: true
  daily_at: "07:00"        # 24h HH:MM
  timezone: "America/Los_Angeles"

recommender:
  enabled: true
  max_concurrent: 3        # max parallel Ollama scoring calls
  score_model: null        # null => reuse ollama.model
```

The `OLLAMA_BASE_URL` environment variable overrides `ollama.base_url` (set automatically in Docker Compose).

---

## User Preferences & Recommendations

- Click 👍 or 👎 on any article — saved immediately to `data/preferences.json`
- The next pipeline run will generate a personal profile from your votes and score today's articles 0–100
- Articles are ordered by score by default; switch to "Fresh Winds" (newest) or "Rising Sun" (most upvoted)
- Your profile summary is visible at `GET /api/profile`

---

## Adding New Sources

See [`docs/adding-sources.md`](docs/adding-sources.md) for a full guide including the scraper contract, registration steps, and worked examples.

---

## Data files

| Path | Contents |
|---|---|
| `data/bulletins/{date}.json` | One bulletin per day; items include `recommendation_score` after a run with preferences |
| `data/preferences.json` | Your like/dislike votes |
| `data/profile.json` | LLM-generated user interest profile |

Bulletins older than `retention_days` are deleted automatically.

---

## Troubleshooting

**Bulletin is empty after refresh**
- Check Ollama is running: `ollama serve` and `ollama list`
- Confirm the model name matches `config.yaml`
- Check server logs for scraper errors

**`Connection refused` / Ollama not reachable in Docker**
- Confirm Ollama is running on your host
- `OLLAMA_BASE_URL` is set to `http://host.docker.internal:11434` in `docker-compose.yml`

**Recommendations not changing**
- Vote on a few articles first, then trigger a refresh
- Check `data/preferences.json` was written
- Check `data/profile.json` was written after the refresh

---

## Project structure

```
src/
  api.py            # FastAPI app
  pipeline.py       # run_pipeline() + asyncio.Lock
  scheduler.py      # APScheduler wrapper
  preferences.py    # preferences.json + profile.json I/O
  recommender.py    # profile refresh + item scoring
  graph.py          # LangGraph pipeline
  config.py         # Config loader
  summarizer.py     # Ollama summarization
  storage.py        # JSON bulletin storage
  scrapers/
    hackernews.py
    reddit.py
    tldr.py
    papers.py
static/
  app.js            # SPA frontend
templates/
  bulletin.html.j2  # Jinja2 shell
docs/
  adding-sources.md
data/               # Generated JSON (git-ignored)
config.yaml
docker-compose.yml
Dockerfile
```
