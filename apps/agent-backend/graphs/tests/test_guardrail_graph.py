"""Tests for Guardrail Agent workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.fixture
def guardrail_state():
    return {
        "query": "What is AI?",
        "session_id": "test-session",
        "primary_response": "",
        "validation_result": None,
        "feedback": "",
        "iteration_count": 0,
        "final_output": "",
        "pydantic_message_history": [],
    }


@pytest.mark.asyncio
async def test_primary_agent_node(guardrail_state, mock_writer):
    from graphs.guardrail_graph import primary_agent_node

    with patch("graphs.guardrail_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("AI is artificial intelligence.", b"[]")
        result = await primary_agent_node(guardrail_state, mock_writer)

        assert result["primary_response"] == "AI is artificial intelligence."


@pytest.mark.asyncio
async def test_guardrail_node_valid(guardrail_state, mock_writer):
    from graphs.guardrail_graph import guardrail_node

    guardrail_state["primary_response"] = "AI is artificial intelligence."

    with patch("graphs.guardrail_graph.guardrail_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "VALID"
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await guardrail_node(guardrail_state, mock_writer)

        assert result["validation_result"] == "valid"
        assert result["final_output"] == "AI is artificial intelligence."


@pytest.mark.asyncio
async def test_guardrail_node_invalid(guardrail_state, mock_writer):
    from graphs.guardrail_graph import guardrail_node

    guardrail_state["primary_response"] = "AI is a fruit."

    with patch("graphs.guardrail_graph.guardrail_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "INVALID - AI is not a fruit"
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await guardrail_node(guardrail_state, mock_writer)

        assert result["validation_result"] == "invalid"
        assert result["feedback"] == "AI is not a fruit"
        assert result["iteration_count"] == 1


@pytest.mark.asyncio
async def test_fallback_node(guardrail_state, mock_writer):
    from graphs.guardrail_graph import fallback_node

    guardrail_state["primary_response"] = "Best effort response."
    guardrail_state["iteration_count"] = 3

    result = await fallback_node(guardrail_state, mock_writer)

    assert result["final_output"] == "Best effort response."
    assert result["fallback_triggered"] is True


def test_route_after_guardrail_valid():
    from graphs.guardrail_graph import route_after_guardrail

    assert route_after_guardrail({"validation_result": "valid"}) == "end"


def test_route_after_guardrail_retry():
    from graphs.guardrail_graph import route_after_guardrail

    assert route_after_guardrail({"validation_result": "invalid", "iteration_count": 1}) == "primary_agent_node"


def test_route_after_guardrail_max_iterations():
    from graphs.guardrail_graph import route_after_guardrail

    assert route_after_guardrail({"validation_result": "invalid", "iteration_count": 3}) == "fallback_node"


def test_workflow_structure():
    from graphs.guardrail_graph import workflow

    assert "primary_agent_node" in workflow.nodes
    assert "guardrail_node" in workflow.nodes
    assert "fallback_node" in workflow.nodes
