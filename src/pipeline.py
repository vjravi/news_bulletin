import asyncio

_lock = asyncio.Lock()
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from src.graph import build_graph
        _graph = build_graph()
    return _graph


async def run_pipeline(config: dict = None, model: str = None) -> dict:
    from src.config import load_config
    if config is None:
        config = load_config()
    if model:
        config = {**config, "llm": {**config["llm"], "model": model}}
    from src.graph import PipelineState
    initial_state: PipelineState = {
        "config": config,
        "raw_items": [],
        "summarized_items": [],
        "bulletin_path": "",
    }
    return await asyncio.wait_for(
        _get_graph().ainvoke(initial_state),
        timeout=1800,
    )


async def try_run_pipeline(config: dict = None, model: str = None) -> bool:
    """Try to acquire the lock and run. Returns False if already running."""
    if _lock.locked():
        return False
    async with _lock:
        await run_pipeline(config, model)
    return True
