# Adding New Sources and Agents

## The Scraper Contract

Every scraper is an `async` function that returns `list[dict]`. Each dict must have these keys:

| Key | Type | Description |
|---|---|---|
| `id` | `str` | **Stable** unique identifier. Must not change between runs for the same article (votes reference this). Use a deterministic hash — e.g. `hashlib.md5(url.encode()).hexdigest()[:12]` or a stable API ID. Do **not** use Python's `hash()` (PYTHONHASHSEED is random). |
| `title` | `str` | Article headline |
| `url` | `str` | Link to the full article |
| `source` | `str` | Short source key used in filtering (e.g. `"hackernews"`, `"reddit"`, `"arxiv"`) |
| `category` | `str` | Display label on the card badge |
| `timestamp` | `str` | ISO 8601 datetime, e.g. `"2026-05-20T08:00:00"` |
| `score` | `int \| None` | Upvote/engagement count; `None` if not applicable |
| `raw_text` | `str` | Content passed to the summarizer; stripped from the item before storage |

**Error handling**: your scraper must not raise. Catch all exceptions, print a warning, and return `[]`.

```python
import hashlib
import httpx

async def scrape_example(max_items: int = 10) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://example.com/feed.json")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[scraper/example] Error: {e}")
        return []

    items = []
    for entry in data["articles"][:max_items]:
        items.append({
            "id": "example-" + hashlib.md5(entry["url"].encode()).hexdigest()[:12],
            "title": entry["title"],
            "url": entry["url"],
            "source": "example",
            "category": "Tech",
            "timestamp": entry["published_at"],
            "score": entry.get("views"),
            "raw_text": entry.get("body", entry["title"]),
        })
    return items
```

## Registering the Scraper in the Pipeline

1. **Add the scraper file** to `src/scrapers/` (e.g. `src/scrapers/example.py`).

2. **Import it** in `src/graph.py`:
   ```python
   from src.scrapers.example import scrape_example
   ```

3. **Add a task** in `_scrape_all()` (around line 35):
   ```python
   if sources.get("example", {}).get("enabled"):
       max_items = sources["example"].get("max_items", 10)
       tasks.append(scrape_example(max_items))
   ```

4. **Add a config block** in `config.yaml`:
   ```yaml
   sources:
     example:
       enabled: true
       max_items: 10
   ```

5. **Add a sidebar entry** in `static/app.js` — extend the `SOURCES` array at the top:
   ```js
   { key: "example", label: "Example Feed", icon: "rss_feed" },
   ```
   The `icon` field is a [Material Symbols](https://fonts.google.com/icons) name.

## Example A: Adding a new subreddit

No new scraper needed. The existing `scrape_reddit` accepts a list of subreddits. Just edit `config.yaml`:

```yaml
sources:
  reddit:
    enabled: true
    subreddits:
      - "LocalLLaMA"
      - "MachineLearning"   # <-- add here
    max_items: 20
```

Each subreddit's posts are fetched and mixed into the `reddit` source category.

## Example B: Adding arXiv as a new source

**1. Create `src/scrapers/arxiv.py`:**

```python
import hashlib
import httpx
from bs4 import BeautifulSoup
from datetime import datetime


async def scrape_arxiv(query: str = "cs.LG", max_items: int = 10) -> list[dict]:
    url = f"https://arxiv.org/search/?query={query}&searchtype=all&start=0"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[scraper/arxiv] Error: {e}")
        return []

    items = []
    for li in soup.select("li.arxiv-result")[:max_items]:
        title_el = li.select_one(".title")
        link_el = li.select_one(".title a")
        abstract_el = li.select_one(".abstract")
        if not title_el or not link_el:
            continue
        paper_url = "https://arxiv.org" + link_el["href"]
        items.append({
            "id": "arxiv-" + hashlib.md5(paper_url.encode()).hexdigest()[:12],
            "title": title_el.get_text(strip=True),
            "url": paper_url,
            "source": "arxiv",
            "category": "Research",
            "timestamp": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            "score": None,
            "raw_text": abstract_el.get_text(strip=True) if abstract_el else "",
        })
    return items
```

**2. Register in `src/graph.py`** inside `_scrape_all()`:
```python
from src.scrapers.arxiv import scrape_arxiv

if sources.get("arxiv", {}).get("enabled"):
    tasks.append(scrape_arxiv(
        sources["arxiv"].get("query", "cs.LG"),
        sources["arxiv"].get("max_items", 10),
    ))
```

**3. Add to `config.yaml`:**
```yaml
sources:
  arxiv:
    enabled: true
    query: "cs.LG"
    max_items: 10
```

**4. Add to the sidebar in `static/app.js`:**
```js
{ key: "arxiv", label: "arXiv", icon: "article" },
```

That's it — the summarizer, recommender, and storage all handle the new source automatically.
