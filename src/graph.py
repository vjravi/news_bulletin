"""
LangGraph pipeline: scrape -> summarize -> store -> refresh_profile -> score_items
Run with: python -m src.graph
"""

import asyncio
from datetime import date
from typing import TypedDict
from langgraph.graph import StateGraph, END

from src.config import load_config
from src.scrapers.hackernews import scrape_hackernews
from src.scrapers.reddit import scrape_reddit
from src.scrapers.tldr import scrape_tldr
from src.scrapers.papers import scrape_huggingface_papers
from src.summarizer import summarize_items
from src.storage import save_bulletin, load_bulletin, list_bulletin_dates, update_bulletin_scores
from src.preferences import load_preferences, load_profile


class PipelineState(TypedDict):
    config: dict
    raw_items: list[dict]
    summarized_items: list[dict]
    bulletin_path: str


# ── Node: scrape all sources in parallel ────────────────────────────────────

async def _scrape_all(config: dict) -> list[dict]:
    sources = config.get("sources", {})
    tasks = []

    if sources.get("hackernews", {}).get("enabled"):
        max_items = sources["hackernews"].get("max_items", 20)
        tasks.append(scrape_hackernews(max_items))

    if sources.get("reddit", {}).get("enabled"):
        subreddits = sources["reddit"].get("subreddits", ["LocalLLaMA"])
        max_items = sources["reddit"].get("max_items", 15)
        tasks.append(scrape_reddit(subreddits, max_items))

    if sources.get("tldr", {}).get("enabled"):
        tasks.append(scrape_tldr())

    if sources.get("papers", {}).get("enabled"):
        filter_type = sources["papers"].get("filter", "date")
        tasks.append(scrape_huggingface_papers(filter_type))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    items = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[scraper error] {r}")
        else:
            items.extend(r)
    return items


async def scrape_node(state: PipelineState) -> PipelineState:
    print("[scrape] Fetching all sources...")
    items = await _scrape_all(state["config"])
    print(f"[scrape] Got {len(items)} items")
    return {**state, "raw_items": items}


# ── Node: summarize ──────────────────────────────────────────────────────────

async def summarize_node(state: PipelineState) -> PipelineState:
    cfg = state["config"]["llm"]
    model = cfg["model"]
    api_base = cfg.get("api_base")
    items = state["raw_items"]
    print(f"[summarize] Summarizing {len(items)} items with {model}...")
    summarized = await summarize_items(items, model, api_base)
    print("[summarize] Done")
    return {**state, "summarized_items": summarized}


# ── Node: store ──────────────────────────────────────────────────────────────

def storage_node(state: PipelineState) -> PipelineState:
    storage_cfg = state["config"]["storage"]
    path = save_bulletin(
        state["summarized_items"],
        storage_cfg["data_dir"],
        storage_cfg.get("retention_days", 7),
    )
    print(f"[storage] Saved bulletin to {path}")
    return {**state, "bulletin_path": str(path)}


# ── Node: refresh user profile ───────────────────────────────────────────────

async def refresh_profile_node(state: PipelineState) -> PipelineState:
    data_dir = state["config"]["storage"]["data_dir"]
    prefs = load_preferences(data_dir)
    if not prefs.get("votes"):
        print("[recommender] No votes yet, skipping profile refresh")
        return state

    print("[recommender] Refreshing user profile...")
    from src.recommender import refresh_profile
    await refresh_profile(state["config"])
    print("[recommender] Profile updated")
    return state


# ── Node: score items ────────────────────────────────────────────────────────

async def score_items_node(state: PipelineState) -> PipelineState:
    cfg = state["config"]
    if not cfg.get("recommender", {}).get("enabled", True):
        return state

    data_dir = cfg["storage"]["data_dir"]
    profile = load_profile(data_dir)
    if not profile.get("summary"):
        print("[recommender] No profile yet, skipping scoring")
        return state

    today = date.today().isoformat()
    bulletin = load_bulletin(data_dir, today)
    items = bulletin.get("items", [])
    if not items:
        return state

    print(f"[recommender] Scoring {len(items)} items...")
    from src.recommender import score_items
    scores = await score_items(items, profile["summary"], cfg)
    update_bulletin_scores(data_dir, today, scores)
    print("[recommender] Scoring complete")
    return state


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("scrape", scrape_node)
    g.add_node("summarize", summarize_node)
    g.add_node("storage", storage_node)
    g.add_node("refresh_profile", refresh_profile_node)
    g.add_node("score_items", score_items_node)

    g.set_entry_point("scrape")
    g.add_edge("scrape", "summarize")
    g.add_edge("summarize", "storage")
    g.add_edge("storage", "refresh_profile")
    g.add_edge("refresh_profile", "score_items")
    g.add_edge("score_items", END)

    return g.compile()


def run():
    from src.pipeline import try_run_pipeline
    import asyncio
    result = asyncio.run(try_run_pipeline())
    print("\nDone!")
    return result


if __name__ == "__main__":
    run()
