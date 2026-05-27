"""
Guardrail Agent Architecture with LangGraph (Module 7.4)

Pattern: Query → Primary Agent → Guardrail → [Valid? END] : [Feedback → Primary Agent]
Up to 3 iterations before fallback.
"""

import os
from typing import Optional, List
from dataclasses import dataclass

from langgraph.graph import StateGraph, START, END
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage

from graphs.state import GuardrailState
from graphs.utils import get_model, stream_agent_response
from tools.web_search import web_search as _web_search
from tools.rag_search import retrieve_relevant_documents as _rag_search
from tools.code_execution import execute_python_code
from tools.sql_query import execute_sql_query
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client


@dataclass
class GuardrailDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: Optional[str]
    searxng_base_url: Optional[str]
    feedback: str = ""


def _create_deps(feedback: str = ""):
    from clients import get_embedding_client, get_supabase_client
    from httpx import AsyncClient
    return GuardrailDeps(
        supabase=get_supabase_client(),
        embedding_client=get_embedding_client(),
        http_client=AsyncClient(),
        brave_api_key=os.getenv("BRAVE_API_KEY") or None,
        searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
        feedback=feedback,
    )


# ─── Primary Agent ────────────────────────────────────────────────────────────

PRIMARY_PROMPT = """You are an intelligent AI assistant with access to research and analysis tools.
Provide accurate, well-researched responses.

CRITICAL: If guardrail feedback is provided, address ALL issues mentioned."""

primary_agent = Agent(get_model(), system_prompt=PRIMARY_PROMPT, deps_type=GuardrailDeps)


@primary_agent.system_prompt
def add_feedback(ctx: RunContext[GuardrailDeps]) -> str:
    if ctx.deps.feedback:
        return f"\n\nGUARDRAIL FEEDBACK (address these issues):\n{ctx.deps.feedback}\n"
    return ""


@primary_agent.tool
async def web_search(ctx: RunContext[GuardrailDeps], query: str) -> str:
    return await _web_search(query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url)


@primary_agent.tool
async def retrieve_documents(ctx: RunContext[GuardrailDeps], user_query: str) -> str:
    return await _rag_search(ctx.deps.supabase, ctx.deps.embedding_client, user_query)


@primary_agent.tool
async def code_execution(ctx: RunContext[GuardrailDeps], code: str) -> str:
    return await execute_python_code(code)


@primary_agent.tool
async def sql_query(ctx: RunContext[GuardrailDeps], query: str) -> str:
    return await execute_sql_query(ctx.deps.supabase, query)


# ─── Guardrail Agent ──────────────────────────────────────────────────────────

GUARDRAIL_PROMPT = """You are a quality assurance guardrail. Validate AI responses for:
1. Factual accuracy
2. Citation quality (if applicable)
3. Relevance to query
4. Completeness
5. Safety

Output format:
- "VALID" if the response is good
- "INVALID - <specific feedback>" if issues found

Be strict but fair."""

guardrail_agent = Agent(get_model(), system_prompt=GUARDRAIL_PROMPT)


# ─── LangGraph Nodes ──────────────────────────────────────────────────────────

MAX_ITERATIONS = 3


async def primary_agent_node(state: GuardrailState, writer) -> dict:
    """Generate response with optional feedback."""
    iteration = state.get("iteration_count", 0) + 1
    if iteration > 1:
        print(f"[guardrail] generating response (attempt {iteration}/{MAX_ITERATIONS})")
    else:
        print("[guardrail] generating response")

    deps = _create_deps(feedback=state.get("feedback") or "")
    message_history = state.get("pydantic_message_history", [])
    full_response, new_messages = await stream_agent_response(
        primary_agent, state["query"], deps, writer, message_history
    )
    return {
        "primary_response": full_response,
        "message_history": [new_messages],
    }


async def guardrail_node(state: GuardrailState, writer) -> dict:
    """Validate the primary agent's response."""
    print("[guardrail] validating response")

    validation_query = f"""User Query: {state['query']}

AI Response:
{state['primary_response']}

Validate this response. Output "VALID" or "INVALID - <feedback>"."""

    result = await guardrail_agent.run(validation_query)
    validation = result.output.strip()

    if validation.upper() == "VALID" or validation.upper().startswith("VALID"):
        print("[guardrail] validation passed")
        return {
            "validation_result": "valid",
            "final_output": state["primary_response"],
            "guardrail_message": "Validation passed",
        }

    feedback = validation
    if validation.upper().startswith("INVALID"):
        feedback = validation[len("INVALID"):].strip("-\n ")

    print(f"[guardrail] issues found: {feedback}")
    return {
        "validation_result": "invalid",
        "feedback": feedback,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "guardrail_message": feedback,
    }


async def fallback_node(state: GuardrailState, writer) -> dict:
    """Return best-effort after max iterations."""
    print(f"[guardrail] max iterations ({MAX_ITERATIONS}) reached, returning best effort")
    return {
        "final_output": state["primary_response"],
        "fallback_triggered": True,
    }


# ─── Conditional Routing ──────────────────────────────────────────────────────

def route_after_guardrail(state: GuardrailState) -> str:
    """Route based on validation result."""
    if state.get("validation_result") == "valid":
        return "end"

    iteration = state.get("iteration_count", 0)
    if iteration >= MAX_ITERATIONS:
        return "fallback_node"

    return "primary_agent_node"


# ─── Workflow Builder ─────────────────────────────────────────────────────────

def create_workflow():
    builder = StateGraph(GuardrailState)
    builder.add_node("primary_agent_node", primary_agent_node)
    builder.add_node("guardrail_node", guardrail_node)
    builder.add_node("fallback_node", fallback_node)

    builder.add_edge(START, "primary_agent_node")
    builder.add_edge("primary_agent_node", "guardrail_node")
    builder.add_conditional_edges(
        "guardrail_node",
        route_after_guardrail,
        {"primary_agent_node": "primary_agent_node", "fallback_node": "fallback_node", "end": END},
    )
    builder.add_edge("fallback_node", END)

    return builder.compile()


workflow = create_workflow()


def create_initial_state(
    query: str,
    session_id: str,
    request_id: str,
    pydantic_message_history: Optional[List[ModelMessage]] = None,
) -> GuardrailState:
    return {
        "query": query,
        "session_id": session_id,
        "request_id": request_id,
        "primary_response": "",
        "validation_result": None,
        "feedback": "",
        "iteration_count": 0,
        "final_output": "",
        "streaming_success": True,
        "message_history": [],
        "pydantic_message_history": pydantic_message_history or [],
    }
