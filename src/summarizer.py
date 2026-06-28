from src.llm import acomplete

# Shared progress state — written by summarize_items, read by /api/progress
progress = {"done": 0, "total": 0}


async def summarize_item(item: dict, model: str, api_base: str) -> dict:
    """Generate a 2-3 sentence summary via the LLM. Falls back to raw_text on failure."""
    title = item["title"]
    raw_text = item.get("raw_text", "")
    prompt = (
        f"Summarize the following in 2-3 concise sentences suitable for a news bulletin. "
        f"Focus on what's new or interesting. Do not repeat the title.\n\n"
        f"Title: {title}\n"
        f"Content: {raw_text or title}\n\n"
        f"Summary:"
    )

    try:
        summary = await acomplete(prompt, model, api_base)
        if not summary:
            print(f"[summarizer] Empty response for '{title}' — raw_text len={len(raw_text)}")
            summary = raw_text[:300]
    except Exception as e:
        print(f"[summarizer] Failed to summarize '{title}' (model={model}, api_base={api_base}): {type(e).__name__}: {e}")
        summary = raw_text[:300]

    result = {k: v for k, v in item.items() if k != "raw_text"}
    result["summary"] = summary
    return result


async def summarize_items(items: list[dict], model: str, api_base: str) -> list[dict]:
    import asyncio
    print(f"[summarizer] Starting {len(items)} items — model={model} api_base={api_base}")
    progress["done"] = 0
    progress["total"] = len(items)
    sem = asyncio.Semaphore(3)

    async def bounded(item):
        async with sem:
            result = await summarize_item(item, model, api_base)
        progress["done"] += 1
        return result

    tasks = [bounded(item) for item in items]
    results = await asyncio.gather(*tasks)
    # A result "failed" if its summary is just the raw_text fallback (short/empty or truncated raw)
    succeeded = sum(
        1 for i, r in enumerate(results)
        if r.get("summary") and r["summary"] != (items[i].get("raw_text", "") or "")[:300]
    )
    print(f"[summarizer] Done — {succeeded}/{len(results)} succeeded, {len(results) - succeeded} fell back to raw_text")
    return results
