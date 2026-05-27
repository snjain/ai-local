"""Tests for Supervisor Agent workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.fixture
def supervisor_state():
    return {
        "query": "Research quantum computing",
        "session_id": "test-session",
        "shared_state": [],
        "iteration_count": 0,
        "delegate_to": None,
        "reasoning": "",
        "final_response": "",
        "pydantic_message_history": [],
    }


@pytest.mark.asyncio
async def test_supervisor_node_delegates(supervisor_state, mock_writer):
    from graphs.supervisor_graph import supervisor_node

    with patch("graphs.supervisor_graph.supervisor_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "web_research: Find recent quantum computing breakthroughs"
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await supervisor_node(supervisor_state, mock_writer)

        assert result["delegate_to"] == "web_research"
        assert result["iteration_count"] == 1


@pytest.mark.asyncio
async def test_supervisor_node_final_response(supervisor_state, mock_writer):
    from graphs.supervisor_graph import supervisor_node

    with patch("graphs.supervisor_graph.supervisor_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "final_response: Quantum computing is advancing rapidly."
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await supervisor_node(supervisor_state, mock_writer)

        assert result["final_response"] == "Quantum computing is advancing rapidly."
        assert result["delegate_to"] is None


@pytest.mark.asyncio
async def test_supervisor_node_max_iterations(supervisor_state, mock_writer):
    from graphs.supervisor_graph import supervisor_node

    supervisor_state["iteration_count"] = 5

    with patch("graphs.supervisor_graph.supervisor_agent") as mock_agent:
        mock_result = Mock()
        mock_result.output = "web_research: more research"
        mock_agent.run = AsyncMock(return_value=mock_result)

        result = await supervisor_node(supervisor_state, mock_writer)

        assert result["final_response"] == "more research"


@pytest.mark.asyncio
async def test_sub_agent_node(supervisor_state, mock_writer):
    from graphs.supervisor_graph import sub_agent_node

    supervisor_state["delegate_to"] = "web_research"
    supervisor_state["reasoning"] = "Find quantum news"

    with patch("graphs.supervisor_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Research findings here", b"[]")
        result = await sub_agent_node(supervisor_state, mock_writer)

        assert len(result["shared_state"]) == 1
        assert "WEB_RESEARCH RESULT" in result["shared_state"][0]


def test_route_after_supervisor():
    from graphs.supervisor_graph import route_after_supervisor

    assert route_after_supervisor({"final_response": "done"}) == "end"
    assert route_after_supervisor({"delegate_to": "web_research"}) == "sub_agent_node"
    assert route_after_supervisor({}) == "end"


def test_route_after_sub_agent():
    from graphs.supervisor_graph import route_after_sub_agent

    assert route_after_sub_agent({}) == "supervisor_node"


def test_workflow_structure():
    from graphs.supervisor_graph import workflow

    assert "supervisor_node" in workflow.nodes
    assert "sub_agent_node" in workflow.nodes
