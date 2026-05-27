"""Simple CLI for testing the Pydantic AI Agent."""

import asyncio
import sys
from pathlib import Path

# Add parent to path so we can import from root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from httpx import AsyncClient
from agent import agent, AgentDeps
from clients import get_embedding_client, get_supabase_client, get_mem0_client
from config import config


async def run_agent(user_input: str, message_history=None):
    """Run the agent with a single user input."""
    # Get clients
    embedding_client = get_embedding_client()
    supabase = get_supabase_client()

    # Retrieve memories (optional — disabled when DB unreachable)
    memories_str = ""

    async with AsyncClient() as http_client:
        deps = AgentDeps(
            supabase=supabase,
            embedding_client=embedding_client,
            http_client=http_client,
            brave_api_key=config.brave_api_key or None,
            searxng_base_url=config.searxng_base_url or None,
            memories=memories_str,
        )

        result = await agent.run(
            user_input,
            deps=deps,
            message_history=message_history or [],
        )
        return result


async def chat_loop():
    """Interactive chat loop."""
    print("=" * 50)
    print("Pydantic AI Agent — CLI")
    print(f"Model: {config.llm_choice} @ {config.llm_base_url}")
    print("Type 'exit' or 'quit' to stop")
    print("=" * 50)

    message_history = []

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        print("\nAgent: ", end="", flush=True)
        result = await run_agent(user_input, message_history)
        print(result.output)
        message_history = result.all_messages()


if __name__ == "__main__":
    asyncio.run(chat_loop())
