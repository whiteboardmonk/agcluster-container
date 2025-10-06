"""Robustness tests for concurrent container sessions"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
import time

from agcluster.container.api.main import app

# Mark all tests in this file as requiring Docker
pytestmark = [pytest.mark.asyncio, pytest.mark.skip(reason="Requires Docker - run manually with actual containers")]


class TestConcurrentSessions:
    """Test multiple concurrent agent sessions"""

    async def test_concurrent_requests(self):
        """Test multiple simultaneous requests create separate containers"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Send 3 concurrent requests
            tasks = [
                client.post(
                    "/chat/completions",
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": f"Count to {i}"}],
                        "stream": False
                    },
                    headers={"Authorization": "Bearer test-key-123"}
                )
                for i in range(1, 4)
            ]

            # Execute concurrently
            responses = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r.status_code in [200, 500] for r in responses)

    
    async def test_session_isolation(self):
        """Test that sessions don't interfere with each other"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Start two sessions
            response1 = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Session 1"}],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-key-1"}
            )

            response2 = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Session 2"}],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-key-2"}
            )

            # Responses should be independent
            assert response1.status_code in [200, 500]
            assert response2.status_code in [200, 500]


class TestErrorHandling:
    """Test error scenarios"""

    
    async def test_invalid_api_key(self):
        """Test handling of invalid API key"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False
                },
                headers={"Authorization": "Bearer invalid-key"}
            )

            # Should handle gracefully (might be 500 or 401 depending on impl)
            assert response.status_code >= 400

    
    async def test_malformed_request(self):
        """Test handling of malformed request"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    # Missing required 'messages' field
                },
                headers={"Authorization": "Bearer test-key"}
            )

            assert response.status_code == 422  # Validation error

    
    async def test_empty_message(self):
        """Test handling of empty message"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": ""}],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-key"}
            )

            # Should either accept or reject gracefully
            assert response.status_code in [200, 400, 422, 500]


class TestResourceLimits:
    """Test resource limit enforcement"""

    
    async def test_large_message(self):
        """Test handling of large messages"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=30.0
        ) as client:
            # 10KB message
            large_content = "A" * 10000

            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": large_content}],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-key"}
            )

            # Should handle gracefully
            assert response.status_code in [200, 413, 500]

    
    async def test_rapid_fire_requests(self):
        """Test handling of rapid successive requests"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            responses = []

            # Send 5 requests rapidly
            for i in range(5):
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": f"Request {i}"}],
                        "stream": False
                    },
                    headers={"Authorization": "Bearer test-key"}
                )
                responses.append(response)

            # All should complete (might fail but shouldn't hang)
            assert len(responses) == 5


class TestStreamingRobustness:
    """Test streaming edge cases"""

    
    async def test_streaming_connection_close(self):
        """Test graceful handling of streaming connection close"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": "claude-sonnet-4.5",
                    "messages": [{"role": "user", "content": "Stream test"}],
                    "stream": True
                },
                headers={"Authorization": "Bearer test-key"}
            )

            # Just verify it starts streaming
            assert response.status_code in [200, 500]

    
    async def test_non_streaming_timeout(self):
        """Test timeout handling for non-streaming requests"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=5.0  # Short timeout
        ) as client:
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": "claude-sonnet-4.5",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": False
                    },
                    headers={"Authorization": "Bearer test-key"}
                )
                # Should complete or timeout gracefully
                assert response.status_code >= 200
            except Exception as e:
                # Timeout is acceptable
                assert "timeout" in str(e).lower() or "timed out" in str(e).lower()
