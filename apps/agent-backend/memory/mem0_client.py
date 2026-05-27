"""Mem0 memory client — gracefully degrades if Postgres unavailable."""
from mem0 import Memory
import os


def get_mem0_config():
    llm_provider = os.getenv('LLM_PROVIDER', 'ollama')
    embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'ollama')
    config = {}
    if llm_provider == 'ollama':
        config["llm"] = {"provider": "ollama", "config": {
            "model": os.getenv('LLM_CHOICE', 'qwen2.5:7b-instruct-q4_K_M'),
            "temperature": 0.2, "max_tokens": 2000,
            "ollama_base_url": os.getenv('LLM_BASE_URL', 'http://127.0.0.1:11434').replace("/v1", "")
        }}
    if embedding_provider == 'ollama':
        config["embedder"] = {"provider": "ollama", "config": {
            "model": os.getenv('EMBEDDING_MODEL_CHOICE', 'nomic-embed-text'),
            "embedding_dims": 768,
            "ollama_base_url": os.getenv('EMBEDDING_BASE_URL', 'http://127.0.0.1:11434').replace("/v1", "")
        }}
    config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": os.environ.get('DATABASE_URL', ''),
            "collection_name": "mem0_memories",
            "embedding_model_dims": 768
        }
    }
    return config


def get_mem0_client():
    return Memory.from_config(get_mem0_config())
