import litellm

# Don't let LiteLLM phone home or fetch its remote model-cost map; we run fully local.
litellm.telemetry = False


async def acomplete(prompt: str, model: str, api_base: str = None, timeout: float = 60) -> str:
    """Run a single-prompt completion via LiteLLM. Provider is encoded in `model`
    (e.g. "ollama/qwen3:30b-a3b", "anthropic/claude-sonnet-4-6", "openai/gpt-4.1"),
    making callers model-agnostic.

    `api_base` is only relevant for self-hosted providers like Ollama; pass None
    for cloud providers (Anthropic/OpenAI), whose endpoints LiteLLM resolves itself.
    Credentials for cloud providers come from env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY).

    Returns the response text, or "" if the model returned nothing.
    """
    kwargs = {"timeout": timeout}
    # api_base only applies to self-hosted providers (Ollama). Passing the Ollama
    # endpoint to a cloud model makes LiteLLM POST to the wrong server (e.g. an
    # OpenAI request to localhost:11434 → "404 page not found").
    if api_base and model.startswith("ollama/"):
        kwargs["api_base"] = api_base

    resp = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return (resp.choices[0].message.content or "").strip()
