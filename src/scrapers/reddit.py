import httpx
from datetime import datetime, timezone


HEADERS = {"User-Agent": "news-summarizer/1.0"}


async def scrape_reddit(subreddits: list[str], max_items: int = 15) -> list[dict]:
    items = []
    async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit={max_items}"
                resp = await client.get(url)
                resp.raise_for_status()
                posts = resp.json()["data"]["children"]
                for post in posts:
                    d = post["data"]
                    items.append({
                        "id": f"reddit_{d['id']}",
                        "title": d.get("title", ""),
                        "url": d.get("url", f"https://reddit.com{d.get('permalink', '')}"),
                        "source": "reddit",
                        "category": f"r/{sub}",
                        "timestamp": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
                        "score": d.get("score", 0),
                        "raw_text": d.get("selftext", "") or d.get("title", ""),
                    })
            except Exception:
                continue
    return items
