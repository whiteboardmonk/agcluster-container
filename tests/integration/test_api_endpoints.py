"""Integration tests for FastAPI endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from agcluster.container.api.main import app
from agcluster.container.core.container_manager import AgentContainer


@pytest.mark.integration
class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self):
        """Test that root endpoint returns service information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AgCluster Container Runtime"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self):
        """Test that health endpoint returns healthy status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_image" in data


@pytest.mark.integration
class TestChatCompletionsEndpoint:
    """Test chat completions endpoint."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test that missing authorization returns 401."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self):
        """Test that invalid authorization format returns 401."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": "InvalidFormat"},
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_user_message(self):
        """Test that missing user message returns 400."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": "Bearer sk-ant-test"},
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "system", "content": "You are helpful"}]
                }
            )

        assert response.status_code == 400
        assert "No user message" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ephemeral_container_non_streaming(self):
        """Test creating ephemeral container for non-streaming response."""
        # Mock container creation and query
        mock_container = Mock()
        mock_container.agent_id = "test-123"

        async def mock_query(message):
            yield {"type": "message", "data": {"type": "content", "content": "Hello!"}}
            yield {"type": "complete", "status": "success"}

        mock_container.query = mock_query

        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_session_manager.get_or_create_session = AsyncMock(return_value=mock_container)
            mock_session_manager.cleanup_session = AsyncMock()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-test-key"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": False
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "claude-sonnet-4.5"
        assert data["choices"][0]["message"]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_ephemeral_container_streaming(self):
        """Test creating ephemeral container for streaming response."""
        mock_container = Mock()
        mock_container.agent_id = "test-123"

        async def mock_query(message):
            yield {"type": "message", "data": {"type": "content", "content": "Hello"}}
            yield {"type": "message", "data": {"type": "content", "content": " world"}}
            yield {"type": "complete", "status": "success"}

        mock_container.query = mock_query

        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_session_manager.get_or_create_session = AsyncMock(return_value=mock_container)
            mock_session_manager.cleanup_session = AsyncMock()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-test-key"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": True
                    }
                )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE chunks
        content = response.text
        assert "data:" in content
        assert "[DONE]" in content

    @pytest.mark.asyncio
    async def test_existing_agent_container(self):
        """Test using existing agent container."""
        mock_container = Mock()
        mock_container.agent_id = "existing-123"

        async def mock_query(message):
            yield {"type": "message", "data": {"type": "content", "content": "Response"}}
            yield {"type": "complete", "status": "success"}

        mock_container.query = mock_query

        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_session_manager.get_or_create_session = AsyncMock(return_value=mock_container)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-test-key"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": False
                    }
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_not_found(self):
        """Test requesting non-existent agent - session manager raises error."""
        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_session_manager.get_or_create_session = AsyncMock(side_effect=ValueError("Session creation failed"))

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-test-key"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}]
                    }
                )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_container_query_error(self):
        """Test handling of container query error."""
        mock_container = Mock()
        mock_container.agent_id = "test-123"

        async def mock_query(message):
            yield {"type": "error", "message": "Container failed"}

        mock_container.query = mock_query

        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_session_manager.get_or_create_session = AsyncMock(return_value=mock_container)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-test-key"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": False
                    }
                )

        assert response.status_code == 500
        assert "Container failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_api_key_extraction_from_bearer(self):
        """Test that API key is correctly extracted from Bearer token."""
        mock_container = Mock()
        mock_container.agent_id = "test-123"

        async def mock_query(message):
            yield {"type": "message", "data": {"type": "content", "content": "OK"}}
            yield {"type": "complete", "status": "success"}

        mock_container.query = mock_query

        with patch("agcluster.container.api.chat_completions.session_manager") as mock_session_manager:
            mock_get_or_create = AsyncMock(return_value=mock_container)
            mock_session_manager.get_or_create_session = mock_get_or_create

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": "Bearer sk-ant-my-key-123"},
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": False
                    }
                )

        # Verify API key was passed correctly to session manager
        assert response.status_code == 200
        mock_get_or_create.assert_called_once()
        call_kwargs = mock_get_or_create.call_args.kwargs
        assert call_kwargs["api_key"] == "sk-ant-my-key-123"


@pytest.mark.integration
class TestRequestValidation:
    """Test request validation."""

    @pytest.mark.asyncio
    async def test_invalid_request_body(self):
        """Test that invalid request body returns 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": "Bearer sk-ant-test"},
                json={"invalid": "data"}
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_messages_array(self):
        """Test that empty messages array is handled."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": "Bearer sk-ant-test"},
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": []
                }
            )

        # Should fail validation or return 400 for no user message
        assert response.status_code in [400, 422]
