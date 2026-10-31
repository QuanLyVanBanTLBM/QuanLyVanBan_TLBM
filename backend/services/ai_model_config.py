"""Supported provider model IDs used by the AI settings API and UI contract."""

MODEL_CONFIG = {
    "gemini": {
        "llm_models": (
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ),
        "default_llm": "gemini-3.8-flash",
        "embed_model": "models/gemini-embedding-001",
    },
    "openai": {
        "llm_models": ("gpt-4o-mini", "gpt-4o"),
        "default_llm": "gpt-4o-mini",
        "embed_model": "text-embedding-3-small",
    },
}
