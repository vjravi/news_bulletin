# News Summarizer - Product Requirements Document

## Overview

The News Summarizer is a tool within "The ToolShed" ecosystem that aggregates, summarizes, and displays news from curated AI/ML and tech sources. It presents content through the "Oasis Reader" — a sand-themed news bulletin served by a **FastAPI backend** with a JavaScript frontend.

The system scrapes content from multiple sources, uses a local LLM to generate concise summaries, stores results locally, and serves them through a live web interface. A **daily APScheduler cron** keeps the bulletin fresh automatically. Users can **like or dislike articles**, and those preferences drive an **LLM-generated profile** that reorders recommendations.

## Problem

Keeping up with AI/ML news across HackerNews, Reddit, research papers, and newsletters is time-consuming. This tool automates the collection, summarization, and personalized ordering so the user gets a single, scannable bulletin tailored to their interests.

## Sources

Each source maps to a category in the bulletin sidebar:

| Source | URL / Details | Category |
|--------|--------------|----------|
| HackerNews | `https://news.ycombinator.com/` | Top stories from front page |
| Reddit - LocalLLM | `r/LocalLLaMA` subreddit | Hot/top posts |
| TLDR AI | `https://tldr.tech/ai/archives` | Daily AI newsletter digest |
| Trending Papers | `https://huggingface.co/papers` | Filterable by date, week, or month |

Additional sources can be added by following `docs/adding-sources.md`.

## Architecture

### Pipeline: LangGraph

```
[Scraper Nodes] --> [Summarizer Node] --> [Storage Node] --> [Profile Refresh] --> [Score Items]
```

1. **Scraper Nodes** (parallel): `hackernews`, `reddit`, `tldr`, `papers`
2. **Summarizer Node**: Calls Ollama to generate 2-3 sentence summaries
3. **Storage Node**: Writes `data/bulletins/{date}.json`
4. **Profile Refresh Node**: If preferences exist, calls Ollama to regenerate the user profile summary
5. **Score Items Node**: If a profile exists, scores each article 0–100 against the profile and writes scores back to the bulletin JSON

### FastAPI Service

The web interface is served by FastAPI (`src/api.py`):

- `GET /` — SPA shell (Jinja2 template + `static/app.js`)
- `GET /api/bulletins/dates` — list of available bulletin dates
- `GET /api/bulletins/{date}` — bulletin JSON sorted by recommendation score
- `POST /api/preferences` — record a like/dislike
- `DELETE /api/preferences/{item_id}` — clear a vote
- `GET /api/profile` — current LLM-generated user profile
- `POST /api/refresh` — manually trigger the pipeline
- `GET /api/health` — healthcheck

### Scheduler

APScheduler runs in-process as an `AsyncIOScheduler`. The daily run time is configured in `config.yaml` under `scheduler.daily_at`. The pipeline is guarded by an `asyncio.Lock` so cron and manual refreshes can't overlap.

### User Preferences & Recommendations

- Votes (like/dislike) are stored in `data/preferences.json`
- After each pipeline run, liked/disliked articles are passed to Ollama to generate a 3-5 sentence user profile (`data/profile.json`)
- Each article in today's bulletin is then scored 0–100 against that profile
- The `/api/bulletins/{date}` endpoint returns items sorted by score descending
- Cold start (no votes): articles sort by recency

### LLM: Local Ollama

- **Model:** configurable (default `qwen3.5:9b-mlx-bf16`)
- **Endpoint:** `http://localhost:11434`
- **Usage:** summarization, profile generation, per-item scoring
- **Concurrency:** bounded via `asyncio.Semaphore` to avoid overwhelming the local model

### Storage: Local JSON

```
data/
  bulletins/
    2026-05-20.json    # One file per day; items include recommendation_score after pipeline
  preferences.json     # {votes: {item_id: "like"|"dislike"}, updated_at}
  profile.json         # {summary: str, updated_at, seed_ids, model}
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Pipeline orchestration | LangGraph |
| LLM integration | LangChain + Ollama (`ChatOllama`) |
| HTTP scraping | `httpx` (async) + `beautifulsoup4` |
| Web framework | FastAPI + Uvicorn |
| Frontend | Vanilla JS (no build step) |
| Styling | Tailwind CSS (CDN) |
| Scheduler | APScheduler (`AsyncIOScheduler`) |
| Storage | Local filesystem (JSON) |
| Configuration | YAML (`config.yaml`) |

## Project Structure

```
news_summarizer/
  src/
    api.py              # FastAPI app + endpoints
    pipeline.py         # run_pipeline() coroutine + lock
    scheduler.py        # APScheduler wrapper
    preferences.py      # preferences.json + profile.json I/O
    recommender.py      # profile refresh + item scoring
    graph.py            # LangGraph pipeline definition
    config.py           # Load config.yaml
    summarizer.py       # Ollama summarization node
    storage.py          # JSON read/write
    scrapers/
      hackernews.py
      reddit.py
      tldr.py
      papers.py
  static/
    app.js              # SPA: fetch, render, calendar, voting
  templates/
    bulletin.html.j2    # SPA shell (chrome only)
  docs/
    adding-sources.md   # How to add new scrapers
  data/
    bulletins/
    preferences.json
    profile.json
  config.yaml
  requirements.txt
  docker-compose.yml
  Dockerfile
```

## Configuration (`config.yaml`)

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
    filter: "date"

storage:
  data_dir: "./data"
  retention_days: 30

scheduler:
  enabled: true
  daily_at: "07:00"
  timezone: "America/Los_Angeles"

recommender:
  enabled: true
  max_concurrent: 3
  score_model: null   # null => reuse ollama.model
```

## User Workflow

1. **Start the server:** `uvicorn src.api:app` (or `docker compose up`)
2. **Open:** `http://localhost:8000`
3. **Read:** Articles appear ordered by personal recommendation score (or recency on first run)
4. **Vote:** Click 👍 or 👎 on any article — stored immediately
5. **Profile updates:** Next pipeline run regenerates your profile from votes and rescores the day's articles
6. **Navigate history:** Use the calendar widget in the sidebar to browse past bulletins
7. **Manual refresh:** Click the Refresh button in the header (or `POST /api/refresh`)

## Future Enhancements

- Additional sources (Arxiv, lobste.rs, newsletters)
- Full-text search with local index
- Bookmark/pin persistence
- Multi-user support
- Topic clustering across sources
- Integration with other ToolShed tools
