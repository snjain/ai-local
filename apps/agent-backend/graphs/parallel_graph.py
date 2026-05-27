"""
Parallel Agents Architecture with LangGraph (Module 7.6)

Pattern: Query → [Parallel: Web | RAG | Code] → Synthesis → END
"""

import os
from typing import Optional, List
from dataclasses import dataclass

from langgraph.graph import StateGraph, START, END
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage

from graphs.state import ParallelState
from graphs.utils import get_model, stream_agent_response
from tools.web_search import web_search as _web_search
from tools.rag_search import retrieve_relevant_documents as _rag_search
from tools.code_execution import execute_python_code
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client


@dataclass
class ParallelDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: Optional[str]
    searxng_base_url: Optional[str]


def _create_deps():
    from clients import get_embedding_client, get_supabase_client
    from httpx import AsyncClient
    return ParallelDeps(
        supabase=get_supabase_client(),
        embedding_client=get_embedding_client(),
        http_client=AsyncClient(),
        brave_api_key=os.getenv("BRAVE_API_KEY") or None,
        searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
    )


# ─── Research Agents ──────────────────────────────────────────────────────────

WEB_PROMPT = """You are a web research specialist. Search the web for current, factual information.
Provide 3-5 bullet points with key findings and sources. Under 300 words."""

RAG_PROMPT = """You are a document research specialist. Search the knowledge base for relevant info.
Provide 3-5 bullet points. Cite document sources. Under 300 words."""

CODE_PROMPT = """You are a data analytics specialist. Use Python to analyze data or verify facts.
Provide 3-5 bullet points with analysis results. Under 300 words."""

web_research_agent = Agent(get_model(), system_prompt=WEB_PROMPT, deps_type=ParallelDeps)
rag_research_agent = Agent(get_model(), system_prompt=RAG_PROMPT, deps_type=ParallelDeps)
analytics_agent = Agent(get_model(), system_prompt=CODE_PROMPT, deps_type=ParallelDeps)


@web_research_agent.tool
async def search_web(ctx: RunContext[ParallelDeps], query: str) -> str:
    return await _web_search(query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url)


@rag_research_agent.tool
async def search_docs(ctx: RunContext[ParallelDeps], query: str) -> str:
    return await _rag_search(ctx.deps.supabase, ctx.deps.embedding_client, query)


@analytics_agent.tool
async def run_analysis(ctx: RunContext[ParallelDeps], code: str) -> str:
    return await execute_python_code(code)


# ─── Synthesis Agent ──────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are a synthesis specialist. Combine research findings from multiple sources
into a single coherent response. Resolve contradictions, highlight unique insights,
and maintain factual accuracy. Be comprehensive but concise."""

synthesis_agent = Agent(get_model(), system_prompt=SYNTHESIS_PROMPT)


# ─── LangGraph Nodes ──────────────────────────────────────────────────────────

async def web_research_node(state: ParallelState, writer) -> dict:
    """Web research agent (parallel)."""
    deps = _create_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, _ = await stream_agent_response(
        web_research_agent, state["query"], deps, writer, message_history
    )
    return {"web_result": full_response}


async def rag_research_node(state: ParallelState, writer) -> dict:
    """Document research agent (parallel)."""
    deps = _create_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, _ = await stream_agent_response(
        rag_research_agent, state["query"], deps, writer, message_history
    )
    return {"rag_result": full_response}


async def code_research_node(state: ParallelState, writer) -> dict:
    """Analytics agent (parallel)."""
    deps = _create_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, _ = await stream_agent_response(
        analytics_agent, state["query"], deps, writer, message_history
    )
    return {"code_result": full_response}


async def synthesis_node(state: ParallelState, writer) -> dict:
    """Combine all parallel findings."""
    synthesis_input = f"""User Query: {state['query']}

=== WEB RESEARCH ===
{state.get('web_result', 'No web results.')}

=== DOCUMENT RESEARCH ===
{state.get('rag_result', 'No document results.')}

=== DATA ANALYSIS ===
{state.get('code_result', 'No analysis results.')}

Synthesize these findings into a comprehensive response."""

    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        synthesis_agent, synthesis_input, None, writer, message_history
    )
    return {
        "final_response": full_response,
        "synthesis": full_response,
        "message_history": [new_messages],
    }


# ─── Workflow Builder ─────────────────────────────────────────────────────────

def create_workflow():
    builder = StateGraph(ParallelState)

    builder.add_node("web_research_node", web_research_node)
    builder.add_node("rag_research_node", rag_research_node)
    builder.add_node("code_research_node", code_research_node)
    builder.add_node("synthesis_node", synthesis_node)

    # Fan-out: all three research agents run in parallel
    builder.add_edge(START, "web_research_node")
    builder.add_edge(START, "rag_research_node")
    builder.add_edge(START, "code_research_node")

    # Fan-in: synthesis waits for all three
    builder.add_edge("web_research_node", "synthesis_node")
    builder.add_edge("rag_research_node", "synthesis_node")
    builder.add_edge("code_research_node", "synthesis_node")

    builder.add_edge("synthesis_node", END)

    return builder.compile()


workflow = create_workflow()


def create_initial_state(
    query: str,
    session_id: str,
    request_id: str,
    pydantic_message_history: Optional[List[ModelMessage]] = None,
) -> ParallelState:
    return {
        "query": query,
        "session_id": session_id,
        "request_id": request_id,
        "web_result": "",
        "rag_result": "",
        "code_result": "",
        "synthesis": "",
        "final_response": "",
        "streaming_success": True,
        "message_history": [],
        "pydantic_message_history": pydantic_message_history or [],
    }
