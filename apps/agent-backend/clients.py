"""Client setup for LLMs, databases, and memory."""

from mem0 import Memory, AsyncMemory
from openai import AsyncOpenAI
from supabase import Client, create_client

from config import config


def get_embedding_client() -> AsyncOpenAI:
    """Create an async OpenAI-compatible client for embeddings."""
    return AsyncOpenAI(
        base_url=config.embedding_base_url,
        api_key=config.embedding_api_key,
    )


def get_supabase_client() -> Client:
    """Create a Supabase client."""
    return create_client(config.supabase_url, config.supabase_service_key)


def get_mem0_config() -> dict:
    """Build Mem0 configuration from settings."""
    mem0_config = {}

    # LLM config
    if config.llm_provider in ("openai", "openrouter"):
        mem0_config["llm"] = {
            "provider": "openai",
            "config": {
                "model": config.llm_choice,
                "temperature": 0.2,
                "max_tokens": 2000,
            },
        }
    elif config.llm_provider == "ollama":
        mem0_config["llm"] = {
            "provider": "ollama",
            "config": {
                "model": config.llm_choice,
                "temperature": 0.2,
                "max_tokens": 2000,
                "ollama_base_url": config.llm_base_url.replace("/v1", ""),
            },
        }

    # Embedder config
    if config.embedding_provider == "openai":
        mem0_config["embedder"] = {
            "provider": "openai",
            "config": {
                "model": config.embedding_model_choice,
                "embedding_dims": 1536,
            },
        }
    elif config.embedding_provider == "ollama":
        mem0_config["embedder"] = {
            "provider": "ollama",
            "config": {
                "model": config.embedding_model_choice,
                "embedding_dims": 768,
                "ollama_base_url": config.embedding_base_url.replace("/v1", ""),
            },
        }

    # Vector store (Supabase/Postgres)
    mem0_config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": config.database_url,
            "collection_name": "mem0_memories",
            "embedding_model_dims": 1536 if config.embedding_provider == "openai" else 768,
        },
    }

    return mem0_config


def get_mem0_client() -> Memory:
    """Create a synchronous Mem0 memory client."""
    return Memory.from_config(get_mem0_config())


async def get_mem0_client_async() -> AsyncMemory:
    """Create an async Mem0 memory client."""
    return await AsyncMemory.from_config(get_mem0_config())
