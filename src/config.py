import os
import yaml
from pathlib import Path


REQUIRED_KEYS = ["ollama", "sources", "storage", "output"]


def load_config(path: str = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"
    with open(path) as f:
        config = yaml.safe_load(f)

    missing = [k for k in REQUIRED_KEYS if k not in config]
    if missing:
        raise ValueError(f"config.yaml is missing required keys: {missing}")

    # Allow env var to override Ollama URL (useful in Docker)
    if os.environ.get("OLLAMA_BASE_URL"):
        config["ollama"]["base_url"] = os.environ["OLLAMA_BASE_URL"]

    return config
