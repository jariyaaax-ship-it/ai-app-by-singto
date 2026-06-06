from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


APP_NAME = "Gemising"
MODEL_NAME = "gemini-3.1-flash-lite"
OLLAMA_DEFAULT_MODEL = "llama3.1"


def _data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME / "Data"
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME / "Config"
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".config" / APP_NAME


DATA_DIR = _data_dir()
CONFIG_DIR = _config_dir()
HISTORY_FILE = DATA_DIR / "chat_history.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    api_key: str = ""
    provider: str = "gemini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = OLLAMA_DEFAULT_MODEL
    enable_google_search: bool = False
    enable_url_context: bool = False
    url_context_sources: str = ""


def load_settings() -> Settings:
    if not SETTINGS_FILE.exists():
        return Settings()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return Settings()
    return Settings(
        api_key=str(data.get("api_key", "")),
        provider=str(data.get("provider", "gemini")),
        ollama_base_url=str(data.get("ollama_base_url", "http://localhost:11434")),
        ollama_model=str(data.get("ollama_model", OLLAMA_DEFAULT_MODEL)),
        enable_google_search=bool(data.get("enable_google_search", False)),
        enable_url_context=bool(data.get("enable_url_context", False)),
        url_context_sources=str(data.get("url_context_sources", "")),
    )


def save_settings(settings: Settings) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
