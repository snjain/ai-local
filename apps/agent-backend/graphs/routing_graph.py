"""
LLM Routing Architecture with LangGraph (Module 7.5)

Pattern: Router → [Conditional] → Specialized Agent → END
"""

import os
from typing import Literal, Optional, List
from dataclasses import dataclass

from langgraph.graph import StateGraph, START, END
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage

from graphs.state import RouterState
from graphs.utils import get_model, stream_agent_response
from tools.web_search import web_search as _web_search
from tools.rag_search import retrieve_relevant_documents as _rag_search
from tools.code_execution import execute_python_code
from tools.sql_query import execute_sql_query
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client


# ─── Dependencies ─────────────────────────────────────────────────────────────

@dataclass
class RouterDeps:
    session_id: str


@dataclass
class SearchDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: Optional[str]
    searxng_base_url: Optional[str]


# ─── Router Agent ─────────────────────────────────────────────────────────────

VALID_DECISIONS = {"web_search", "rag_search", "code_execution", "sql_query", "fallback"}

ROUTER_PROMPT = """You are a query classifier. Analyze the user's query and decide which specialized agent should handle it.

Available options:
- web_search: for questions about current events, facts, or anything requiring web search
- rag_search: for questions about uploaded documents or the knowledge base
- code_execution: for questions requiring Python code execution or calculations
- sql_query: for questions requiring database queries
- fallback: for general chat, greetings, or unclear queries

Respond with EXACTLY ONE WORD from the options above. Do not add punctuation or explanations."""

router_agent = Agent(
    get_model(),
    deps_type=RouterDeps,
    system_prompt=ROUTER_PROMPT,
)


# ─── Specialized Agents ───────────────────────────────────────────────────────

WEB_PROMPT = "You are a web research specialist. Search the web and summarize findings with sources."
RAG_PROMPT = "You are a document research specialist. Search the knowledge base and cite sources."
CODE_PROMPT = "You are a Python code execution specialist. Write and run code, explain results."
SQL_PROMPT = "You are a SQL query specialist. Execute SELECT queries and present results."
FALLBACK_PROMPT = "You are a helpful assistant. Answer general questions or ask for clarification."

web_search_agent = Agent(get_model(), system_prompt=WEB_PROMPT, deps_type=SearchDeps)
rag_search_agent = Agent(get_model(), system_prompt=RAG_PROMPT, deps_type=SearchDeps)
code_execution_agent = Agent(get_model(), system_prompt=CODE_PROMPT, deps_type=SearchDeps)
sql_query_agent = Agent(get_model(), system_prompt=SQL_PROMPT, deps_type=SearchDeps)
fallback_agent = Agent(get_model(), system_prompt=FALLBACK_PROMPT, deps_type=SearchDeps)


@web_search_agent.tool
async def search_web(ctx: RunContext[SearchDeps], query: str) -> str:
    return await _web_search(query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url)


@rag_search_agent.tool
async def search_documents(ctx: RunContext[SearchDeps], query: str) -> str:
    return await _rag_search(ctx.deps.supabase, ctx.deps.embedding_client, query)


@code_execution_agent.tool
async def run_code(ctx: RunContext[SearchDeps], code: str) -> str:
    return await execute_python_code(code)


@sql_query_agent.tool
async def run_sql(ctx: RunContext[SearchDeps], query: str) -> str:
    return await execute_sql_query(ctx.deps.supabase, query)


# ─── LangGraph Nodes ──────────────────────────────────────────────────────────

def _create_search_deps():
    from clients import get_embedding_client, get_supabase_client
    from httpx import AsyncClient
    return SearchDeps(
        supabase=get_supabase_client(),
        embedding_client=get_embedding_client(),
        http_client=AsyncClient(),
        brave_api_key=os.getenv("BRAVE_API_KEY") or None,
        searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
    )


async def router_node(state: RouterState, writer) -> dict:
    """Classify query and route to appropriate agent."""
    try:
        deps = RouterDeps(session_id=state.get("session_id", ""))
        message_history = state.get("pydantic_message_history", [])
        result = await router_agent.run(state["query"], deps=deps, message_history=message_history)
        raw = str(result.output).strip().lower()
        # Extract decision word from response (handle extra text)
        decision = "fallback"
        for d in VALID_DECISIONS:
            if d in raw:
                decision = d
                break
        print(f"[router] routing to: {decision}")
        return {"routing_decision": decision, "router_confidence": "high"}
    except Exception as e:
        print(f"Router error: {e}")
        return {"routing_decision": "fallback", "router_confidence": "fallback"}


async def web_search_node(state: RouterState, writer) -> dict:
    """Web search agent node."""
    deps = _create_search_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        web_search_agent, state["query"], deps, writer, message_history
    )
    return {
        "final_response": full_response,
        "agent_type": "web_search",
        "message_history": [new_messages],
    }


async def rag_search_node(state: RouterState, writer) -> dict:
    """RAG search agent node."""
    deps = _create_search_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        rag_search_agent, state["query"], deps, writer, message_history
    )
    return {
        "final_response": full_response,
        "agent_type": "rag_search",
        "message_history": [new_messages],
    }


async def code_execution_node(state: RouterState, writer) -> dict:
    """Code execution agent node."""
    deps = _create_search_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        code_execution_agent, state["query"], deps, writer, message_history
    )
    return {
        "final_response": full_response,
        "agent_type": "code_execution",
        "message_history": [new_messages],
    }


async def sql_query_node(state: RouterState, writer) -> dict:
    """SQL query agent node."""
    deps = _create_search_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        sql_query_agent, state["query"], deps, writer, message_history
    )
    return {
        "final_response": full_response,
        "agent_type": "sql_query",
        "message_history": [new_messages],
    }


async def fallback_node(state: RouterState, writer) -> dict:
    """Fallback for unclear queries."""
    deps = _create_search_deps()
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        fallback_agent, state["query"], deps, writer, message_history
    )
    return {
        "final_response": full_response,
        "agent_type": "fallback",
        "message_history": [new_messages],
    }


# ─── Conditional Routing ──────────────────────────────────────────────────────

def route_based_on_decision(state: RouterState) -> str:
    decision = state.get("routing_decision", "fallback")
    mapping = {
        "web_search": "web_search_node",
        "rag_search": "rag_search_node",
        "code_execution": "code_execution_node",
        "sql_query": "sql_query_node",
        "fallback": "fallback_node",
    }
    return mapping.get(decision, "fallback_node")


# ─── Workflow Builder ─────────────────────────────────────────────────────────

def create_workflow():
    builder = StateGraph(RouterState)
    builder.add_node("router_node", router_node)
    builder.add_node("web_search_node", web_search_node)
    builder.add_node("rag_search_node", rag_search_node)
    builder.add_node("code_execution_node", code_execution_node)
    builder.add_node("sql_query_node", sql_query_node)
    builder.add_node("fallback_node", fallback_node)

    builder.add_edge(START, "router_node")
    builder.add_conditional_edges(
        "router_node",
        route_based_on_decision,
        {
            "web_search_node": "web_search_node",
            "rag_search_node": "rag_search_node",
            "code_execution_node": "code_execution_node",
            "sql_query_node": "sql_query_node",
            "fallback_node": "fallback_node",
        },
    )
    builder.add_edge("web_search_node", END)
    builder.add_edge("rag_search_node", END)
    builder.add_edge("code_execution_node", END)
    builder.add_edge("sql_query_node", END)
    builder.add_edge("fallback_node", END)

    return builder.compile()


workflow = create_workflow()


def create_initial_state(
    query: str,
    session_id: str,
    request_id: str,
    pydantic_message_history: Optional[List[ModelMessage]] = None,
) -> RouterState:
    return {
        "query": query,
        "session_id": session_id,
        "request_id": request_id,
        "routing_decision": "",
        "router_confidence": "",
        "final_response": "",
        "agent_type": "",
        "streaming_success": True,
        "message_history": [],
        "pydantic_message_history": pydantic_message_history or [],
    }
