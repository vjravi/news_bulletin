import httpx
import json


async def summarize_item(item: dict, model: str, base_url: str) -> dict:
    """Call Ollama to generate a 2-3 sentence summary. Falls back to raw_text on failure."""
    prompt = (
        f"Summarize the following in 2-3 concise sentences suitable for a news bulletin. "
        f"Focus on what's new or interesting. Do not repeat the title.\n\n"
        f"Title: {item['title']}\n"
        f"Content: {item.get('raw_text', item['title'])}\n\n"
        f"Summary:"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("response", "").strip()
    except Exception as e:
        print(f"[summarizer] Warning: failed to summarize '{item['title']}': {e}")
        summary = item.get("raw_text", "")[:300]

    result = {k: v for k, v in item.items() if k != "raw_text"}
    result["summary"] = summary
    return result


async def summarize_items(items: list[dict], model: str, base_url: str) -> list[dict]:
    import asyncio
    tasks = [summarize_item(item, model, base_url) for item in items]
    return await asyncio.gather(*tasks)
