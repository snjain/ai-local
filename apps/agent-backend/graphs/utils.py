"""Shared utilities for LangGraph workflows."""

import os
from typing import Optional, List
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from pydantic_ai.messages import PartStartEvent, PartDeltaEvent, TextPartDelta

from clients import get_embedding_client, get_supabase_client


def get_model(use_smaller_model: bool = False):
    """Create an OpenAI-compatible model pointing to Ollama."""
    llm = os.getenv('LLM_CHOICE') or 'qwen2.5:7b-instruct-q4_K_M'
    base_url = os.getenv('LLM_BASE_URL') or 'https://api.openai.com/v1'
    api_key = os.getenv('LLM_API_KEY') or 'ollama'
    return OpenAIChatModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))


async def stream_agent_response(
    agent: Agent,
    agent_input: str,
    deps,
    writer,
    message_history: Optional[List] = None,
) -> tuple[str, bytes]:
    """
    Stream a Pydantic AI agent response through a LangGraph writer.

    Returns (full_response, new_messages_bytes).
    """
    full_response = ""
    new_messages = b""

    try:
        async with agent.iter(agent_input, deps=deps, message_history=message_history or []) as run:
            async for node in run:
                if agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                writer(event.part.content)
                                full_response += event.part.content
                            elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                delta = event.delta.content_delta
                                writer(delta)
                                full_response += delta

        # Capture final messages
        if run.result:
            if run.result.output and not full_response:
                full_response = str(run.result.output)
                writer(full_response)
            new_messages = run.result.new_messages_json()

    except Exception as stream_error:
        # Fallback to non-streaming
        print(f"Streaming failed, using fallback: {stream_error}")

        result = await agent.run(agent_input, deps=deps, message_history=message_history or [])
        full_response = str(result.output) if result.output else "No response generated."
        writer(full_response)
        new_messages = result.new_messages_json()

    return full_response, new_messages
