"""
LangGraph pipeline: scrape -> summarize -> store -> render
Run with: python -m src.graph
"""

import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END

from src.config import load_config
from src.scrapers.hackernews import scrape_hackernews
from src.scrapers.reddit import scrape_reddit
from src.scrapers.tldr import scrape_tldr
from src.scrapers.papers import scrape_huggingface_papers
from src.summarizer import summarize_items
from src.storage import save_bulletin, load_bulletin
from src.renderer import render_bulletin


class PipelineState(TypedDict):
    config: dict
    raw_items: list[dict]
    summarized_items: list[dict]
    bulletin_path: str
    html_path: str


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
    cfg = state["config"]["ollama"]
    model = cfg["model"]
    base_url = cfg["base_url"]
    items = state["raw_items"]
    print(f"[summarize] Summarizing {len(items)} items with {model}...")
    summarized = await summarize_items(items, model, base_url)
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


# ── Node: render ─────────────────────────────────────────────────────────────

def renderer_node(state: PipelineState) -> PipelineState:
    storage_cfg = state["config"]["storage"]
    output_cfg = state["config"]["output"]
    bulletin = load_bulletin(storage_cfg["data_dir"])
    html_path = render_bulletin(bulletin, output_cfg["html_path"])
    print(f"[renderer] HTML written to {html_path}")
    return {**state, "html_path": str(html_path)}


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("scrape", scrape_node)
    g.add_node("summarize", summarize_node)
    g.add_node("storage", storage_node)
    g.add_node("renderer", renderer_node)

    g.set_entry_point("scrape")
    g.add_edge("scrape", "summarize")
    g.add_edge("summarize", "storage")
    g.add_edge("storage", "renderer")
    g.add_edge("renderer", END)

    return g.compile()


def run():
    config = load_config()
    graph = build_graph()
    initial_state: PipelineState = {
        "config": config,
        "raw_items": [],
        "summarized_items": [],
        "bulletin_path": "",
        "html_path": "",
    }
    final = asyncio.run(graph.ainvoke(initial_state))
    print(f"\nDone! Open {final['html_path']} in your browser.")
    return final


if __name__ == "__main__":
    run()
