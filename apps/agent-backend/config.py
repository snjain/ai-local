"""Centralized configuration for the Pydantic AI Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


class AgentConfig(BaseSettings):
    """Agent configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"
    llm_choice: str = "qwen2.5:7b-instruct-q4_K_M"
    vision_llm_choice: str = "llava:7b"

    # Embeddings
    embedding_provider: str = "ollama"
    embedding_base_url: str = "http://127.0.0.1:11434/v1"
    embedding_api_key: str = "ollama"
    embedding_model_choice: str = "nomic-embed-text"

    # Supabase
    supabase_url: str = "http://127.0.0.1:8000"
    supabase_service_key: str = ""

    # Mem0 / Postgres
    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    # Web Search
    brave_api_key: str = ""
    searxng_base_url: str = "http://127.0.0.1:8080"  # Use http://searxng:8080 when running inside Docker

    @property
    def is_local(self) -> bool:
        return self.llm_provider == "ollama"


# Singleton config instance
config = AgentConfig()
