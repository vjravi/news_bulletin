# Code Review — News Summarizer

## Critical Bugs

**1. `src/scrapers/papers.py` — `resp.text` accessed after the `async with` block closes the connection** ✅ RESOLVED

The `BeautifulSoup` call is outside the `async with httpx.AsyncClient` block. The connection is already closed, so `resp.text` may be empty or raise — silently returning zero papers.

Fix: move the soup parse inside the block (as `tldr.py` does correctly).

---

**2. `src/summarizer.py` — bare `except Exception` with no logging** ✅ RESOLVED

If Ollama is down, every item silently falls back to raw text and the pipeline reports `"[summarize] Done"` with no warning. Debugging requires reading the HTML output.

Fix: `except Exception as e: print(f"[summarizer] Warning: ...")`

---

**3. `templates/bulletin.html.j2` — potential XSS via `javascript:` URLs in `href`** ✅ RESOLVED

`autoescape=True` handles HTML entities but not `javascript:` URLs in `href` attributes. URLs come from external scraped sources.

Fix: add a `safe_url` Jinja2 filter in `renderer.py` that strips anything not starting with `http://` or `https://`, and use `{{ item.url | safe_url }}` in the template.

---

**4. `src/graph.py` — `asyncio.run()` inside node functions breaks if LangGraph runs async** ✅ RESOLVED

`asyncio.run()` raises `RuntimeError` when called inside an already-running event loop. LangGraph's `.ainvoke()` mode will break this silently. Node functions should be `async def` using `await`.

---

**5. `src/graph.py` — no config validation; missing keys crash deep in the pipeline** ✅ RESOLVED

The `config.yaml` volume-mount in Docker makes it easy to accidentally supply a partial config. Add a `REQUIRED_KEYS` check at load time.

---

## Suggestions

| # | Location | Issue |
|---|----------|-------|
| S1 | `src/scrapers/hackernews.py` | 20 sequential HTTP requests — should use `asyncio.gather` |
| S2 | `src/scrapers/tldr.py`, `src/scrapers/papers.py` | `hash()` is per-process random (PYTHONHASHSEED); use `hashlib.md5` for stable IDs |
| S3 | `src/summarizer.py` | `asyncio.gather` with 50+ concurrent Ollama requests will overwhelm the local model — add a `Semaphore(3)` |
| S4 | `requirements.txt` | `fastapi` and `uvicorn` are unused; remove them. All packages unpinned. |
| S5 | `Dockerfile` | Container runs as root unnecessarily — add `useradd` + `USER appuser` |
| S6 | `src/graph.py:98` | `renderer_node` reloads the bulletin from disk that `storage_node` just wrote — pass it through state directly |
| S7 | `src/graph.py:52` | Zero scraped items silently produces an empty bulletin with no error |
