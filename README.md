# News Summarizer — Oasis Reader

Aggregates AI/ML news from HackerNews, Reddit (r/LocalLLaMA), TLDR AI, and HuggingFace Papers, summarizes each item with a local LLM, and serves a personalized reading bulletin via FastAPI.

**Pipeline:** scrape (parallel) → summarize via an LLM → store JSON → refresh user profile → score items by relevance

The LLM layer is wrapped with [LiteLLM](https://docs.litellm.ai), so the summarizer and recommender are model-agnostic — run a local model through Ollama, or point at Anthropic Claude or OpenAI by changing one config line (see [Configuration](#configuration)).

**Serve:** FastAPI + vanilla JS frontend with a calendar archive and like/dislike voting

---

## Quickstart (local)

### Prerequisites

- Python 3.11+
- An LLM backend. By default this is [Ollama](https://ollama.com) running locally with the model pulled:

```bash
ollama pull qwen3:30b-a3b
```

(To use Anthropic Claude or OpenAI instead, see [Configuration](#configuration) — no local model needed.)

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
- [Ollama](https://ollama.com) running on your host machine (or a cloud LLM provider — see [Configuration](#configuration))

```bash
ollama pull qwen3:30b-a3b
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
llm:
  # Provider-agnostic via LiteLLM. The provider is encoded in the model string.
  model: "ollama/qwen3:30b-a3b"
  api_base: "http://localhost:11434"   # used by Ollama; ignored for cloud providers

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
  max_concurrent: 3        # max parallel scoring calls
  score_model: null        # null => reuse llm.model
```

### Choosing an LLM provider

The summarizer and recommender call the LLM through [LiteLLM](https://docs.litellm.ai), so switching providers is a config change. The provider is encoded in the `llm.model` string; `llm.api_base` is only used for self-hosted backends like Ollama.

| Provider | `llm.model` | `llm.api_base` | Credentials |
|---|---|---|---|
| **Ollama** (local, default) | `ollama/qwen3:30b-a3b` | `http://localhost:11434` | none |
| **Anthropic Claude** | `anthropic/claude-opus-4-8` | _(omit / leave unused)_ | `ANTHROPIC_API_KEY` env var |
| **OpenAI** | `openai/gpt-4.1` | _(omit / leave unused)_ | `OPENAI_API_KEY` env var |

To use a cloud provider:

1. Set `llm.model` to the provider-prefixed model string (e.g. `anthropic/claude-opus-4-8` or `openai/gpt-4.1`). For Claude, see the [model list](https://docs.anthropic.com/en/docs/about-claude/models) — e.g. `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`.
2. Export the matching API key before starting the server:

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."   # for Claude
   export OPENAI_API_KEY="sk-..."           # for OpenAI
   ```

3. `llm.api_base` is ignored for cloud providers — leave it as-is or remove it. No local model or Ollama is required.

The `LLM_API_BASE` environment variable overrides `llm.api_base` (and the legacy `OLLAMA_BASE_URL` is still honored — set automatically in Docker Compose). These only affect self-hosted backends.

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
- If using Ollama: check it's running (`ollama serve` and `ollama list`) and that the model matches `config.yaml` (`llm.model` without the `ollama/` prefix)
- If using a cloud provider: confirm the matching API key env var is set (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`)
- Check server logs for scraper or LLM errors

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
