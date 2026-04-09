import httpx
from datetime import datetime, timezone


HN_API = "https://hacker-news.firebaseio.com/v0"


async def scrape_hackernews(max_items: int = 20) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{HN_API}/topstories.json")
        resp.raise_for_status()
        story_ids = resp.json()[:max_items]

        items = []
        for sid in story_ids:
            try:
                r = await client.get(f"{HN_API}/item/{sid}.json")
                r.raise_for_status()
                data = r.json()
                if not data or data.get("type") != "story":
                    continue
                items.append({
                    "id": f"hn_{sid}",
                    "title": data.get("title", ""),
                    "url": data.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "source": "hackernews",
                    "category": "Technology",
                    "timestamp": datetime.fromtimestamp(data.get("time", 0), tz=timezone.utc).isoformat(),
                    "score": data.get("score", 0),
                    "raw_text": data.get("title", ""),
                })
            except Exception:
                continue

        return items
