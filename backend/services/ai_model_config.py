"""Supported provider model IDs used by the AI settings API and UI contract."""

MODEL_CONFIG = {
    "openai": {
        "llm_models": ("gpt-6-luna",),
        "default_llm": "gpt-6-luna",
        "embed_model": "text-embedding-3-large",
    },
}
