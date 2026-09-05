"""Provider constants live here. Secrets are read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
GEMINI_OPENAI_BASE_URL = os.getenv(
    "GEMINI_OPENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)

_DEFAULT_CHAT_MODELS = {
    "ollama": "qwen2.5:7b",
    "openrouter": "nvidia/nemotron-3.5-lightning:free",
    "openai": "gpt-4o-mini",
    "mistral": "mistral-small",
}

LLM_PROVIDER = "mistral"
EMBEDDING_PROVIDER = "gemini"
LOCAL_MODEL = LLM_PROVIDER == "ollama"

LANGFUSE_TRACING = True
LANGFUSE_ENVIRONMENT = "development"
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")

DEFAULT_EMBEDDING_MODELS = {
    "hf": "BAAI/bge-m3",
    "gemini": "gemini-embedding-001",
    "openai": "text-embedding-3-small",
}

_EMBEDDING_MODEL_OWNERS = {
    model: provider for provider, model in DEFAULT_EMBEDDING_MODELS.items()
}


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _chat_model(provider: str) -> str:
    if model := os.getenv("MODEL"):
        return model
    env_name = {
        "openai": "OPENAI_MODEL",
        "ollama": "OLLAMA_MODEL",
        "openrouter": "OPENROUTER_MODEL",
        "mistral": "MISTRAL_MODEL",
    }.get(provider)
    if env_name and (value := os.getenv(env_name)):
        return value
    return _DEFAULT_CHAT_MODELS.get(provider, "gpt-4o-mini")


def _embedding_model(provider: str) -> str:
    if model := os.getenv("EMBEDDING_MODEL"):
        resolved = model
    elif provider == "openai" and (value := os.getenv("OPENAI_EMBEDDING_MODEL")):
        resolved = value
    else:
        resolved = DEFAULT_EMBEDDING_MODELS.get(provider, "BAAI/bge-m3")
    owner = _EMBEDDING_MODEL_OWNERS.get(resolved)
    if owner is not None and owner != provider:
        raise ValueError(
            "Provider model mismatch, please check your config.py file "
            f"(EMBEDDING_PROVIDER='{provider}' is not compatible with "
            f"EMBEDDING_MODEL='{resolved}')."
        )
    return resolved


def _llm_provider() -> str:
    return LLM_PROVIDER.strip().lower()


def _api_key(provider: str) -> str | None:
    if provider == "ollama":
        return "ollama"
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider == "openrouter":
        return os.getenv("OPEN_ROUTER_API_KEY")
    if provider == "mistral":
        return os.getenv("MISTRAL_API_KEY")
    return None


def _embedding_api_key(provider: str) -> str | None:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY")
    return None


@dataclass(frozen=True)
class Settings:
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
    llm_provider: str
    model: str
    api_key: str | None
    embedding_provider: str
    embedding_model: str
    embedding_api_key: str | None
    google_service_account_file: str
    agent_tracing: bool
    langfuse_public_key: str | None
    langfuse_secret_key: str | None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def langfuse_enabled(self) -> bool:
        return (
            LANGFUSE_TRACING
            and bool(self.langfuse_public_key)
            and bool(self.langfuse_secret_key)
        )


def _load_settings() -> Settings:
    llm_provider = _llm_provider()
    embedding_provider = EMBEDDING_PROVIDER.strip().lower()
    return Settings(
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        postgres_host=os.environ["POSTGRES_HOST"],
        postgres_port=os.environ["POSTGRES_PORT"],
        postgres_db=os.environ["POSTGRES_DB"],
        llm_provider=llm_provider,
        model=_chat_model(llm_provider),
        api_key=_api_key(llm_provider),
        embedding_provider=embedding_provider,
        embedding_model=_embedding_model(embedding_provider),
        embedding_api_key=_embedding_api_key(embedding_provider),
        google_service_account_file=os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            str(PROJECT_ROOT / "secrets" / "google_service_account.json"),
        ),
        agent_tracing=_bool("AGENT_TRACING", default=False),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
    )


settings = _load_settings()


def require_embedding_provider(provider: str, current: Settings) -> str:
    """Return the configured embedding model, or raise if `provider` does not match."""
    if current.embedding_provider != provider:
        raise ValueError(
            "Provider model mismatch, please check your config.py file "
            f"(configured provider is '{current.embedding_provider}' "
            f"with model '{current.embedding_model}', "
            f"but '{provider}' was requested)."
        )
    return current.embedding_model
