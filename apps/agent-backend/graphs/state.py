"""Shared state definitions for LangGraph workflows."""

from typing import TypedDict, List, Optional
from pydantic_ai.messages import ModelMessage


class BaseAgentState(TypedDict, total=False):
    """Base state shared across all architecture patterns."""
    query: str
    session_id: str
    request_id: str
    final_response: str
    message_history: List[bytes]
    pydantic_message_history: List[ModelMessage]
    streaming_success: bool
    conversation_title: Optional[str]
    is_new_conversation: bool
    agent_type: str


class RouterState(BaseAgentState, total=False):
    """State for LLM Routing workflow."""
    routing_decision: str
    router_confidence: str


class ParallelState(BaseAgentState, total=False):
    """State for Parallel Agents workflow."""
    web_result: str
    rag_result: str
    code_result: str
    synthesis: str
    sources: dict


class SupervisorState(BaseAgentState, total=False):
    """State for Supervisor Agent workflow."""
    shared_state: List[str]
    iteration_count: int
    delegate_to: Optional[str]
    reasoning: str


class GuardrailState(BaseAgentState, total=False):
    """State for Guardrail Agent workflow."""
    primary_response: str
    validation_result: Optional[str]
    feedback: Optional[str]
    iteration_count: int
    guardrail_message: Optional[str]
    fallback_triggered: Optional[bool]
