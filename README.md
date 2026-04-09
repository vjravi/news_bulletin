# News Summarizer — Oasis Reader

Aggregates AI/ML news from HackerNews, Reddit (r/LocalLLaMA), TLDR AI, and HuggingFace Papers, summarizes each item with a local LLM, and renders a static HTML bulletin.

**Pipeline:** scrape (parallel) → summarize via Ollama → store JSON → render HTML

## Running with Docker (recommended)

### Prerequisites

- Docker and Docker Compose
- [Ollama](https://ollama.com) running on your host machine with the model pulled

### 1. Start Ollama and pull the model

```bash
# Pull the model (one-time, ~5 GB)
ollama pull qwen3.5:9b
```

The pipeline connects to Ollama running on your host — no separate Ollama container needed.

### 2. Run the pipeline

```bash
docker compose --profile run up pipeline --build
```

This builds the pipeline image, runs all scrapers in parallel, summarizes each article via the local LLM, and writes the output.

### 3. Open the bulletin

```
open output/bulletin.html
```

Or just double-click `output/bulletin.html` in Finder.

---

## Running locally (without Docker)

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally with the model pulled

```bash
ollama pull qwen3.5:9b
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the pipeline

```bash
python -m src.graph
```

Output is written to `output/bulletin.html`.

---

## Configuration

Edit `config.yaml` to change sources, model, or output paths:

```yaml
ollama:
  model: "qwen3.5:9b"          # any model pulled in Ollama
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
    filter: "date"            # date | week | month

storage:
  data_dir: "./data"
  retention_days: 7

output:
  html_path: "./output/bulletin.html"
```

The `OLLAMA_BASE_URL` environment variable overrides `ollama.base_url` in the config — this is set automatically in Docker Compose, but you can also set it locally:

```bash
OLLAMA_BASE_URL=http://192.168.1.10:11434 python -m src.graph
```

---

## Troubleshooting

**`Connection refused` / Ollama not reachable**
- Ensure Ollama is running: `ollama serve`
- Check the model is pulled: `ollama list`
- Verify `base_url` in `config.yaml` matches where Ollama is listening

**`ValueError: missing required config keys`**
- `config.yaml` must have all four top-level keys: `ollama`, `sources`, `storage`, `output`

**Scraper returns 0 items**
- HackerNews and Reddit are public APIs — check network/firewall
- TLDR AI and HuggingFace Papers scrape HTML; a site layout change may break parsing

**Docker: pipeline can't reach Ollama**
- Ensure Ollama is running on your host: `ollama serve`
- Confirm the model is pulled: `ollama list`

---

## Project structure

```
src/
  graph.py          # LangGraph pipeline (entry point)
  config.py         # Config loader
  summarizer.py     # Ollama summarization node
  storage.py        # JSON bulletin storage
  renderer.py       # Jinja2 HTML renderer
  scrapers/
    hackernews.py
    reddit.py
    tldr.py
    papers.py
templates/
  bulletin.html.j2  # Jinja2 template (sand-themed UI)
data/               # Generated JSON bulletins (git-ignored)
output/             # Generated HTML (git-ignored)
config.yaml
docker-compose.yml
Dockerfile
```

---

## Data

- `data/bulletins/YYYY-MM-DD.json` — one bulletin per day
- Bulletins older than `retention_days` are deleted automatically
- `output/bulletin.html` is regenerated on each run
