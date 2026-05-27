"""Tests for Parallel Agents workflow."""

import pytest
from unittest.mock import patch


@pytest.fixture
def parallel_state():
    return {
        "query": "Analyze AI trends",
        "session_id": "test-session",
        "request_id": "test-request",
        "web_result": "",
        "rag_result": "",
        "code_result": "",
        "final_response": "",
        "pydantic_message_history": [],
    }


@pytest.mark.asyncio
async def test_web_research_node(parallel_state, mock_writer):
    from graphs.parallel_graph import web_research_node

    with patch("graphs.parallel_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Web findings", b"[]")
        result = await web_research_node(parallel_state, mock_writer)
        assert result["web_result"] == "Web findings"


@pytest.mark.asyncio
async def test_rag_research_node(parallel_state, mock_writer):
    from graphs.parallel_graph import rag_research_node

    with patch("graphs.parallel_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Doc findings", b"[]")
        result = await rag_research_node(parallel_state, mock_writer)
        assert result["rag_result"] == "Doc findings"


@pytest.mark.asyncio
async def test_code_research_node(parallel_state, mock_writer):
    from graphs.parallel_graph import code_research_node

    with patch("graphs.parallel_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Analysis results", b"[]")
        result = await code_research_node(parallel_state, mock_writer)
        assert result["code_result"] == "Analysis results"


@pytest.mark.asyncio
async def test_synthesis_node(parallel_state, mock_writer):
    from graphs.parallel_graph import synthesis_node

    parallel_state["web_result"] = "Web: AI is growing"
    parallel_state["rag_result"] = "RAG: Companies investing"
    parallel_state["code_result"] = "Code: 25% growth"

    with patch("graphs.parallel_graph.stream_agent_response") as mock_stream:
        mock_stream.return_value = ("Synthesized report", b"[]")
        result = await synthesis_node(parallel_state, mock_writer)
        assert result["final_response"] == "Synthesized report"
        assert result["synthesis"] == "Synthesized report"


def test_workflow_structure():
    from graphs.parallel_graph import workflow

    assert "web_research_node" in workflow.nodes
    assert "rag_research_node" in workflow.nodes
    assert "code_research_node" in workflow.nodes
    assert "synthesis_node" in workflow.nodes
