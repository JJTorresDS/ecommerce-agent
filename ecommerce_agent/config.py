"""Environment-backed settings. The only module that should read os.environ."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
    local_model: bool
    open_router_api_key: str | None
    ollama_model: str
    ollama_base_url: str
    openrouter_model: str
    embedding_provider: str
    google_service_account_file: str
    agent_tracing: bool

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def _load_settings() -> Settings:
    return Settings(
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        postgres_host=os.environ["POSTGRES_HOST"],
        postgres_port=os.environ["POSTGRES_PORT"],
        postgres_db=os.environ["POSTGRES_DB"],
        local_model=_bool("LOCAL_MODEL", default=False),
        open_router_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free"
        ),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "hf"),
        google_service_account_file=os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            str(PROJECT_ROOT / "secrets" / "google_service_account.json"),
        ),
        agent_tracing=_bool("AGENT_TRACING", default=False),
    )


settings = _load_settings()
