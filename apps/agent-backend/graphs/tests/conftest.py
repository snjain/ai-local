"""Shared fixtures for LangGraph tests."""

import pytest


@pytest.fixture
def mock_writer():
    """Capture streamed output."""
    written = []
    def writer(data):
        written.append(data)
    writer.written = written
    return writer
