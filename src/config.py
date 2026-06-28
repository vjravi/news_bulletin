import os
import yaml
from pathlib import Path


REQUIRED_KEYS = ["llm", "sources", "storage", "output"]


def load_config(path: str = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"
    with open(path) as f:
        config = yaml.safe_load(f)

    missing = [k for k in REQUIRED_KEYS if k not in config]
    if missing:
        raise ValueError(f"config.yaml is missing required keys: {missing}")

    # Allow env var to override the LLM API base (useful in Docker for local Ollama).
    # OLLAMA_BASE_URL kept for backward compat; LLM_API_BASE is the provider-agnostic name.
    api_base_override = os.environ.get("LLM_API_BASE") or os.environ.get("OLLAMA_BASE_URL")
    if api_base_override:
        config["llm"]["api_base"] = api_base_override

    return config
