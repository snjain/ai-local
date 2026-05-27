"""Integration tests for architecture API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from api import app, verify_token


# Override auth dependency for tests
def mock_verify_token():
    return {"id": "test-user-id", "email": "test@example.com"}

app.dependency_overrides[verify_token] = mock_verify_token

# Initialize app.state mocks (lifespan not triggered at module level)
app.state.supabase = Mock()
app.state.http_client = Mock()
app.state.embedding_client = Mock()

client = TestClient(app)


def _make_workflow_mock():
    """Create a mock workflow that yields a stream and final state."""
    mock = Mock()

    async def mock_astream(*args, **kwargs):
        yield ("custom", "Test response")
        yield ("values", {
            "final_response": "Test response",
        })

    mock.astream = mock_astream
    return mock


class TestArchitectureEndpoints:
    """Test architecture endpoints with mocked auth and dependencies."""

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_routing_endpoint_structure(self):
        with patch("api.routing_workflow", _make_workflow_mock()):
            with patch("api.check_rate_limit", AsyncMock(return_value=True)):
                with patch("api.store_request", AsyncMock()):
                    with patch("api.create_conversation", AsyncMock(return_value=None)):
                        with patch("api.store_message", AsyncMock()):
                            with patch("api.fetch_conversation_history", AsyncMock(return_value=[])):
                                with patch("api.convert_history_to_pydantic_format", AsyncMock(return_value=[])):
                                    response = client.post(
                                        "/api/agent-routing",
                                        json={
                                            "query": "What is AI?",
                                            "user_id": "test-user-id",
                                            "request_id": "test-request",
                                            "session_id": "",
                                        },
                                    )
                                    assert response.status_code == 200

    def test_parallel_endpoint_structure(self):
        with patch("api.parallel_workflow", _make_workflow_mock()):
            with patch("api.check_rate_limit", AsyncMock(return_value=True)):
                with patch("api.store_request", AsyncMock()):
                    with patch("api.create_conversation", AsyncMock(return_value=None)):
                        with patch("api.store_message", AsyncMock()):
                            with patch("api.fetch_conversation_history", AsyncMock(return_value=[])):
                                with patch("api.convert_history_to_pydantic_format", AsyncMock(return_value=[])):
                                    response = client.post(
                                        "/api/agent-parallel",
                                        json={
                                            "query": "Analyze trends",
                                            "user_id": "test-user-id",
                                            "request_id": "test-request",
                                            "session_id": "",
                                        },
                                    )
                                    assert response.status_code == 200

    def test_supervisor_endpoint_structure(self):
        with patch("api.supervisor_workflow", _make_workflow_mock()):
            with patch("api.check_rate_limit", AsyncMock(return_value=True)):
                with patch("api.store_request", AsyncMock()):
                    with patch("api.create_conversation", AsyncMock(return_value=None)):
                        with patch("api.store_message", AsyncMock()):
                            with patch("api.fetch_conversation_history", AsyncMock(return_value=[])):
                                with patch("api.convert_history_to_pydantic_format", AsyncMock(return_value=[])):
                                    response = client.post(
                                        "/api/agent-supervisor",
                                        json={
                                            "query": "Research topic",
                                            "user_id": "test-user-id",
                                            "request_id": "test-request",
                                            "session_id": "",
                                        },
                                    )
                                    assert response.status_code == 200

    def test_guardrail_endpoint_structure(self):
        with patch("api.guardrail_workflow", _make_workflow_mock()):
            with patch("api.check_rate_limit", AsyncMock(return_value=True)):
                with patch("api.store_request", AsyncMock()):
                    with patch("api.create_conversation", AsyncMock(return_value=None)):
                        with patch("api.store_message", AsyncMock()):
                            with patch("api.fetch_conversation_history", AsyncMock(return_value=[])):
                                with patch("api.convert_history_to_pydantic_format", AsyncMock(return_value=[])):
                                    response = client.post(
                                        "/api/agent-guardrail",
                                        json={
                                            "query": "Complex question",
                                            "user_id": "test-user-id",
                                            "request_id": "test-request",
                                            "session_id": "",
                                        },
                                    )
                                    assert response.status_code == 200

    def test_rate_limit(self):
        with patch("api.check_rate_limit", AsyncMock(return_value=False)):
            response = client.post(
                "/api/agent-routing",
                json={
                    "query": "Test",
                    "user_id": "test-user-id",
                    "request_id": "test-request",
                    "session_id": "",
                },
            )
            assert response.status_code == 200
            content = response.content.decode()
            assert "Rate limit exceeded" in content

    def test_user_mismatch(self):
        # verify_token returns "test-user-id", but request sends "other-user"
        # Endpoints return StreamingResponse (200) with error streamed in content
        response = client.post(
            "/api/agent-routing",
            json={
                "query": "Test",
                "user_id": "other-user",
                "request_id": "test-request",
                "session_id": "",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "User ID mismatch" in content
