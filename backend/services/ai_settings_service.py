"""AI Settings persistence service.

Stores and retrieves AI settings across Gunicorn/Uvicorn worker processes,
container restarts, and deployment releases via a shared JSON file in DATA_DIR.
"""
import json
import logging
import os
from pathlib import Path

import backend.config as config
from backend.services.ai_model_config import MODEL_CONFIG

logger = logging.getLogger(__name__)
SETTINGS_FILE_NAME = "ai_settings.json"


def get_settings_file_path() -> Path:
    data_dir = getattr(config, "DATA_DIR", None)
    if data_dir is None:
        data_dir = Path(os.getenv("AI_DATA_DIR") or (config.BASE_DIR / "data"))
    return Path(data_dir) / SETTINGS_FILE_NAME


def get_active_ai_settings() -> dict:
    """Return the active AI settings dictionary.

    Priority:
    1. DATA_DIR / ai_settings.json (persisted on disk across workers/restarts)
    2. os.environ / backend.config attributes
    3. Defaults (openai / gpt-6-luna)
    """
    provider = "openai"
    provider_config = MODEL_CONFIG[provider]

    settings = {
        "provider": provider,
        "llm_model": provider_config["default_llm"],
        "embed_model": provider_config["embed_model"],
        "vision_model": provider_config["default_llm"],
        "gemini_api_key": os.getenv("GEMINI_API_KEY") or getattr(config, "GEMINI_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY") or getattr(config, "OPENAI_API_KEY", ""),
    }

    file_path = get_settings_file_path()
    if file_path.exists():
        try:
            stored = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                for k in ("gemini_api_key", "openai_api_key"):
                    val = stored.get(k)
                    if val is not None and str(val).strip():
                        settings[k] = str(val).strip()
        except Exception as exc:
            logger.warning("Could not read ai_settings.json: %s", exc)

    settings.update({
        "provider": provider,
        "llm_model": provider_config["default_llm"],
        "embed_model": provider_config["embed_model"],
        "vision_model": provider_config["default_llm"],
    })
    return settings


def get_active_provider() -> str:
    active = get_active_ai_settings()
    return "openai"


def save_ai_settings(updates: dict) -> dict:
    """Persist settings to DATA_DIR/ai_settings.json and sync to memory/env."""
    current = get_active_ai_settings()
    for k, v in updates.items():
        if v is not None:
            current[k] = str(v).strip()

    # 1. Write to DATA_DIR / ai_settings.json
    file_path = get_settings_file_path()
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not save to %s: %s", file_path, exc)

    # 2. Sync to in-memory attributes and os.environ
    env_keys = {
        "provider": "MODEL_PROVIDER",
        "MODEL_PROVIDER": "MODEL_PROVIDER",
        "llm_model": "LLM_MODEL",
        "LLM_MODEL": "LLM_MODEL",
        "embed_model": "EMBED_MODEL",
        "EMBED_MODEL": "EMBED_MODEL",
        "vision_model": "VISION_MODEL",
        "VISION_MODEL": "VISION_MODEL",
        "gemini_api_key": "GEMINI_API_KEY",
        "GEMINI_API_KEY": "GEMINI_API_KEY",
        "openai_api_key": "OPENAI_API_KEY",
        "OPENAI_API_KEY": "OPENAI_API_KEY",
    }
    for src_key, env_var in env_keys.items():
        if src_key in current and current[src_key]:
            val = str(current[src_key])
            os.environ[env_var] = val
            setattr(config, env_var, val)

    # 3. Best-effort update to .env files
    target_env_paths = [config.BASE_DIR / "backend" / ".env"]
    root_env = config.BASE_DIR / ".env"
    if root_env.exists():
        target_env_paths.append(root_env)

    sync_pairs = {
        "MODEL_PROVIDER": current.get("provider"),
        "LLM_MODEL": current.get("llm_model"),
        "EMBED_MODEL": current.get("embed_model"),
        "VISION_MODEL": current.get("vision_model"),
        "GEMINI_API_KEY": current.get("gemini_api_key"),
        "OPENAI_API_KEY": current.get("openai_api_key"),
    }
    for env_path in target_env_paths:
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
            seen = set()
            output = []
            for line in lines:
                name = line.split("=", 1)[0].strip() if "=" in line else ""
                if name in sync_pairs and sync_pairs[name]:
                    output.append(f"{name}={sync_pairs[name]}")
                    seen.add(name)
                else:
                    output.append(line)
            output.extend(f"{name}={val}" for name, val in sync_pairs.items() if name not in seen and val)
            env_path.write_text("\n".join(output) + "\n", encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not write to %s: %s", env_path, exc)

    return current

