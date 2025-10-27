"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from agcluster.container.api.main import app


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
        assert data["version"] == "0.2.0"
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
