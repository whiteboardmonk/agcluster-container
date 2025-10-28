"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing without Docker daemon."""
    mock_client = Mock()
    mock_container = Mock()
    mock_container.id = "test-container-123"
    mock_container.short_id = "test-123"
    mock_container.status = "running"
    mock_container.attrs = {
        "NetworkSettings": {
            "IPAddress": "172.17.0.2",
            "Ports": {"8765/tcp": [{"HostPort": "8765"}]},
            "Networks": {
                "agcluster-container_agcluster-network": {
                    "IPAddress": "172.17.0.2",
                    "Gateway": "172.17.0.1",
                    "NetworkID": "test-network-id",
                }
            },
        }
    }
    mock_container.logs = Mock(return_value=b"Container started")
    mock_container.stop = Mock()
    mock_container.remove = Mock()
    mock_container.reload = Mock()  # Add reload method

    mock_client.containers.run = Mock(return_value=mock_container)
    mock_client.containers.get = Mock(return_value=mock_container)
    mock_client.containers.list = Mock(return_value=[])

    return mock_client


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection for testing."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(return_value='{"type": "complete", "status": "success"}')
    mock_ws.close = AsyncMock()
    return mock_ws


@pytest.fixture
def sample_openai_request():
    """Sample OpenAI chat completion request."""
    return {
        "model": "claude-sonnet-4.5",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 1000,
    }


@pytest.fixture
def sample_claude_messages():
    """Sample Claude SDK message format."""
    return [{"role": "user", "content": "Hello, how are you?"}]


@pytest.fixture
def sample_anthropic_api_key():
    """Sample Anthropic API key for testing."""
    return "sk-ant-test-key-12345"


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    from agcluster.container.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_client():
    """Synchronous test client for FastAPI."""
    from agcluster.container.api.main import app

    return TestClient(app)
