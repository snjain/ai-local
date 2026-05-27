"""Agent dependencies dataclass."""

from dataclasses import dataclass
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client


@dataclass
class AgentDeps:
    """Dependencies injected into the agent at runtime."""

    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: str | None
    searxng_base_url: str | None
    memories: str
