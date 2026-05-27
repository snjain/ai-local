"""Tests for LLM Routing workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.fixture
def base_state():
    return {
        "query": "What is the weather today?",
        "session_id": "test-session",
        "request_id": "test-request",
        "final_response": "",
        "message_history": [],
        "pydantic_message_history": [],
    }


def test_route_based_on_decision():
    from graphs.routing_graph import route_based_on_decision

    assert route_based_on_decision({"routing_decision": "web_search"}) == "web_search_node"
    assert route_based_on_decision({"routing_decision": "rag_search"}) == "rag_search_node"
    assert route_based_on_decision({"routing_decision": "code_execution"}) == "code_execution_node"
    assert route_based_on_decision({"routing_decision": "sql_query"}) == "sql_query_node"
    assert route_based_on_decision({"routing_decision": "fallback"}) == "fallback_node"
    assert route_based_on_decision({"routing_decision": "unknown"}) == "fallback_node"
    assert route_based_on_decision({}) == "fallback_node"


@pytest.mark.asyncio
async def test_router_node_success(base_state, mock_writer):
    from graphs.routing_graph import router_node

    with patch("graphs.routing_graph.router_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "web_search"
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await router_node(base_state, mock_writer)

        assert result["routing_decision"] == "web_search"
        assert result["router_confidence"] == "high"


@pytest.mark.asyncio
async def test_router_node_error_fallback(base_state, mock_writer):
    from graphs.routing_graph import router_node

    with patch("graphs.routing_graph.router_agent") as mock_agent:
        mock_agent.run = AsyncMock(side_effect=Exception("Model error"))

        result = await router_node(base_state, mock_writer)

        assert result["routing_decision"] == "web_search"
        assert result["router_confidence"] == "fallback"


@pytest.mark.asyncio
async def test_web_search_node(base_state, mock_writer):
    from graphs.routing_graph import web_search_node

    with patch("graphs.routing_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Web search results", b"[]")

        result = await web_search_node(base_state, mock_writer)

        assert result["final_response"] == "Web search results"
        assert result["agent_type"] == "web_search"


@pytest.mark.asyncio
async def test_rag_search_node(base_state, mock_writer):
    from graphs.routing_graph import rag_search_node

    with patch("graphs.routing_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Document results", b"[]")

        result = await rag_search_node(base_state, mock_writer)

        assert result["final_response"] == "Document results"
        assert result["agent_type"] == "rag_search"


@pytest.mark.asyncio
async def test_fallback_node(base_state, mock_writer):
    from graphs.routing_graph import fallback_node

    with patch("graphs.routing_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Fallback response", b"[]")

        result = await fallback_node(base_state, mock_writer)

        assert result["final_response"] == "Fallback response"
        assert result["agent_type"] == "fallback"


def test_workflow_structure():
    from graphs.routing_graph import workflow

    assert "router_node" in workflow.nodes
    assert "web_search_node" in workflow.nodes
    assert "rag_search_node" in workflow.nodes
    assert "fallback_node" in workflow.nodes
