import asyncio
import json
import re
from datetime import datetime

from src.llm import acomplete
from src.preferences import load_preferences, load_profile, save_profile
from src.storage import find_items_by_ids, load_bulletin, list_bulletin_dates


async def refresh_profile(config: dict):
    data_dir = config["storage"]["data_dir"]
    model = config.get("recommender", {}).get("score_model") or config["llm"]["model"]
    api_base = config["llm"].get("api_base")

    prefs = load_preferences(data_dir)
    votes = prefs.get("votes", {})
    if not votes:
        return

    items = find_items_by_ids(data_dir, list(votes.keys()))
    if not items:
        return

    liked = [it for it in items if votes.get(it["id"]) == "like"]
    disliked = [it for it in items if votes.get(it["id"]) == "dislike"]

    liked_block = "\n".join(
        f"- {it['title']}: {it.get('summary', '')}" for it in liked
    ) or "None"
    disliked_block = "\n".join(
        f"- {it['title']}: {it.get('summary', '')}" for it in disliked
    ) or "None"

    prompt = (
        "Based on the articles this user liked and disliked, write a 3-5 sentence profile "
        "describing what they want to read. Be concrete about topics, formats, and what to avoid.\n\n"
        f"LIKED:\n{liked_block}\n\nDISLIKED:\n{disliked_block}\n\nProfile:"
    )

    try:
        summary = await acomplete(prompt, model, api_base)
        if summary:
            save_profile(data_dir, summary, list(votes.keys()), model)
    except Exception as e:
        print(f"[recommender] Warning: failed to refresh profile: {e}")


async def _score_item(item: dict, profile: str, model: str, api_base: str, sem: asyncio.Semaphore) -> dict:
    prompt = (
        f"User profile: {profile}\n\n"
        f"Article title: {item['title']}\n"
        f"Article summary: {item.get('summary', '')}\n\n"
        'Return ONLY a JSON object: {"score": <0-100>, "reason": "<8 words or less>"}'
    )

    async with sem:
        try:
            text = await acomplete(prompt, model, api_base)
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                score = int(data.get("score", 50))
                reason = data.get("reason")
            else:
                score, reason = 50, None
        except Exception as e:
            print(f"[recommender] Warning: failed to score '{item['title']}': {e}")
            score, reason = 50, None

    return {
        "item_id": item["id"],
        "recommendation_score": max(0, min(100, score)),
        "recommendation_reason": reason,
        "scored_at": datetime.now().isoformat(),
    }


async def score_items(items: list[dict], profile: str, config: dict) -> dict:
    model = config.get("recommender", {}).get("score_model") or config["llm"]["model"]
    api_base = config["llm"].get("api_base")
    max_concurrent = config.get("recommender", {}).get("max_concurrent", 3)
    sem = asyncio.Semaphore(max_concurrent)

    results = await asyncio.gather(*[
        _score_item(item, profile, model, api_base, sem) for item in items
    ])

    return {r["item_id"]: r for r in results}
