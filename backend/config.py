"""Loads config/config.yaml and resolves relative paths against the project root."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:14b"
    temperature: float = 0.7
    num_ctx: int = 8192


@dataclass
class WikiDbConfig:
    enabled: bool = True
    path: Path = field(default_factory=lambda: Path("wiki.db"))
    search_limit_per_table: int = 5
    max_context_chars: int = 4000


@dataclass
class ChatHistoryConfig:
    path: Path = field(default_factory=lambda: Path("./data/chat_history.db"))


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class AppConfig:
    ollama: OllamaConfig
    wiki_db: WikiDbConfig
    chat_history: ChatHistoryConfig
    server: ServerConfig


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    ollama_raw = raw.get("ollama", {})
    wiki_raw = raw.get("wiki_db", {})
    history_raw = raw.get("chat_history", {})
    server_raw = raw.get("server", {})

    chat_history_path = _resolve(history_raw.get("path", "./data/chat_history.db"))
    chat_history_path.parent.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        ollama=OllamaConfig(
            host=ollama_raw.get("host", "http://localhost:11434"),
            model=ollama_raw.get("model", "qwen2.5:14b"),
            temperature=float(ollama_raw.get("temperature", 0.7)),
            num_ctx=int(ollama_raw.get("num_ctx", 8192)),
        ),
        wiki_db=WikiDbConfig(
            enabled=bool(wiki_raw.get("enabled", True)),
            path=_resolve(wiki_raw.get("path", "wiki.db")),
            search_limit_per_table=int(wiki_raw.get("search_limit_per_table", 5)),
            max_context_chars=int(wiki_raw.get("max_context_chars", 4000)),
        ),
        chat_history=ChatHistoryConfig(path=chat_history_path),
        server=ServerConfig(
            host=server_raw.get("host", "127.0.0.1"),
            port=int(server_raw.get("port", 8000)),
        ),
    )
