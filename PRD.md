# News Summarizer - Product Requirements Document

## Overview

The News Summarizer is a tool within "The ToolShed" ecosystem that aggregates, summarizes, and displays news from curated AI/ML and tech sources. It presents content through the "Oasis Reader" — a sand-themed news bulletin web page (see `template/code.html`).

The system scrapes content from multiple sources, uses a local LLM to generate concise summaries, and stores results locally for display in the bulletin UI.

## Problem

Keeping up with AI/ML news across HackerNews, Reddit, research papers, and newsletters is time-consuming. Manually visiting each source, reading articles, and synthesizing takeaways is a daily chore. This tool automates the collection and summarization so the user gets a single, scannable bulletin.

## Sources

Each source maps to a category in the bulletin sidebar:

| Source | URL / Details | Category |
|--------|--------------|----------|
| HackerNews | `https://news.ycombinator.com/` | Top stories from front page |
| Reddit - LocalLLM | `r/LocalLLaMA` subreddit | Hot/top posts |
| TLDR AI | `https://tldr.tech/ai/archives` | Daily AI newsletter digest |
| Trending Papers | `https://huggingface.co/papers` | Filterable by date, week, or month (e.g. `/date/2026-04-09`) |

Additional subreddits or sources can be added later by extending the scraper nodes.

## Architecture

### Pipeline: LangGraph

The data pipeline is built with **LangGraph**, defining a directed graph of nodes:

```
[Scraper Nodes] --> [Summarizer Node] --> [Storage Node] --> [Renderer Node]
```

#### Nodes

1. **Scraper Nodes** (one per source, run in parallel)
   - `scrape_hackernews` — Fetches top stories via HN API (`https://hacker-news.firebaseio.com/v0/`)
   - `scrape_reddit` — Fetches hot posts from target subreddits via Reddit JSON API (append `.json` to subreddit URL)
   - `scrape_tldr` — Parses the latest TLDR AI newsletter archive page
   - `scrape_huggingface_papers` — Fetches trending papers from HuggingFace papers page, supports date/week/month filtering

2. **Summarizer Node**
   - Takes raw scraped items as input
   - Calls local Ollama LLM to generate a 2-3 sentence summary per item
   - Extracts: title, source URL, category, timestamp, summary

3. **Storage Node**
   - Writes summarized results to local JSON storage
   - Organizes by date and source
   - Maintains a rolling window (configurable, default 7 days)

4. **Renderer Node**
   - Reads stored JSON data
   - Generates the final HTML bulletin from the Jinja2 template (derived from `template/code.html`)
   - Outputs a static HTML file that can be opened in a browser or served locally

### LLM: Local Ollama

- **Model:** `qwen3.5:9b` running on local Ollama instance
- **Endpoint:** `http://localhost:11434` (default Ollama)
- **Usage:** Summarization only — each scraped item gets a prompt asking for a concise summary
- **Fallback:** If Ollama is unavailable, store raw content without summary

### Storage: Local JSON

- **Location:** `data/` directory in project root
- **Structure:**
  ```
  data/
    bulletins/
      2026-04-09.json    # One file per day
    raw/
      hackernews/
      reddit/
      tldr/
      papers/
  ```
- **Bulletin JSON schema:**
  ```json
  {
    "date": "2026-04-09",
    "generated_at": "2026-04-09T08:30:00",
    "items": [
      {
        "id": "hn_12345",
        "title": "Article Title",
        "url": "https://...",
        "source": "hackernews",
        "category": "Technology",
        "summary": "LLM-generated summary...",
        "timestamp": "2026-04-09T06:00:00",
        "score": 150
      }
    ]
  }
  ```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Pipeline orchestration | LangGraph |
| LLM integration | LangChain + Ollama (`ChatOllama`) |
| HTTP scraping | `httpx` (async) + `beautifulsoup4` for HTML parsing |
| Template rendering | Jinja2 |
| Storage | Local filesystem (JSON) |
| Local server (optional) | `uvicorn` + `FastAPI` for serving the bulletin |
| Configuration | YAML config file (`config.yaml`) |

## Project Structure

```
news_summarizer/
  template/
    code.html              # Design reference (existing)
    screen.png             # Screenshot (existing)
  src/
    __init__.py
    config.py              # Load config.yaml
    graph.py               # LangGraph pipeline definition
    scrapers/
      __init__.py
      hackernews.py
      reddit.py
      tldr.py
      papers.py
    summarizer.py          # Ollama summarization node
    storage.py             # JSON read/write
    renderer.py            # Jinja2 HTML generation
  templates/
    bulletin.html.j2       # Jinja2 template derived from template/code.html
  data/
    bulletins/
    raw/
  config.yaml
  requirements.txt
  README.md
```

## Configuration (`config.yaml`)

```yaml
ollama:
  model: "qwen3.5:9b"
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
    filter: "date"  # date | week | month

storage:
  data_dir: "./data"
  retention_days: 7

output:
  html_path: "./output/bulletin.html"
```

## User Workflow

1. **Run the pipeline:** `python -m src.graph` (or a CLI entry point)
2. **Pipeline executes:** Scrapers run in parallel -> Summarizer processes items -> Storage saves JSON -> Renderer generates HTML
3. **View the bulletin:** Open `output/bulletin.html` in a browser, or run `python -m src.serve` for a local dev server

## UI Mapping

The existing template (`template/code.html`) maps to the data as follows:

- **Sidebar categories** map to sources (HackerNews, Reddit, TLDR, Papers)
- **Filter buttons** (Fresh Winds, Rising Sun, etc.) map to sort/filter options (newest, trending, unread, pinned)
- **Article cards** are rendered from bulletin JSON items — each card shows: category badge, timestamp, title, summary, link to original
- **Search** filters items client-side by title/summary text

## MVP Scope

1. Scrape all 4 sources
2. Summarize with local Ollama (qwen3.5:9b)
3. Store as daily JSON files
4. Render static HTML bulletin from template
5. CLI to run the full pipeline

## Future Enhancements

- Additional sources (Arxiv, Twitter/X, lobste.rs)
- Additional subreddits configurable via YAML
- Scheduled runs (cron / systemd timer)
- Tagging and topic clustering across sources
- Full-text search with local index
- Integration with other ToolShed tools
- Bookmark/pin persistence
