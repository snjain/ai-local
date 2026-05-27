"""Streamlit UI for the Pydantic AI Agent."""

import streamlit as st
import asyncio
from httpx import AsyncClient

from agent import agent, AgentDeps
from clients import get_embedding_client, get_supabase_client
from memory.mem0_client import get_mem0_client
from config import config


@st.cache_resource
def get_deps_cached():
    """Cache agent clients."""
    return get_embedding_client(), get_supabase_client()


@st.cache_resource
def get_memory_cached():
    """Cache Mem0 memory client."""
    try:
        return get_mem0_client()
    except Exception:
        return None


async def run_agent_streaming(user_input: str, message_history):
    """Run agent with conversation history."""
    embedding_client, supabase = get_deps_cached()

    # Retrieve memories (optional — disabled when DB unreachable)
    memories_str = ""
    memory = get_memory_cached()
    if memory:
        try:
            results = memory.search(query=user_input, user_id="streamlit_user", limit=3)
            memories_str = "\n".join(
                f"- {r['memory']}" for r in results.get("results", [])
            )
        except Exception:
            pass

    async with AsyncClient() as http_client:
        deps = AgentDeps(
            supabase=supabase,
            embedding_client=embedding_client,
            http_client=http_client,
            brave_api_key=config.brave_api_key or None,
            searxng_base_url=config.searxng_base_url or None,
            memories=memories_str,
        )

        result = await agent.run(user_input, deps=deps)
        return result


def main():
    st.set_page_config(page_title="Pydantic AI Agent", page_icon="🤖")
    st.title("🤖 Pydantic AI Agent")
    st.caption(f"Model: `{config.llm_choice}` | Provider: `{config.llm_provider}`")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        st.chat_message(role).write(content)

    # Chat input
    user_input = st.chat_input("Ask me anything...")
    if user_input:
        # Display user message
        st.chat_message("user").write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Run agent
        with st.spinner("Thinking..."):
            result = asyncio.run(
                run_agent_streaming(user_input, st.session_state.messages)
            )

        # Display response
        response = result.output
        st.chat_message("assistant").write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
