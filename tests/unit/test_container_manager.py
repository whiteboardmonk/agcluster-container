"""Unit tests for ContainerManager with mocked Docker."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import docker.errors
from datetime import datetime
import asyncio

from agcluster.container.core.container_manager import (
    ContainerManager,
    AgentContainer,
)


@pytest.mark.unit
class TestAgentContainer:
    """Test AgentContainer class."""

    def test_initialization(self):
        """Test AgentContainer initialization."""
        container = AgentContainer(
            agent_id="test-123",
            container_id="container-abc",
            container_ip="172.17.0.2"
        )

        assert container.agent_id == "test-123"
        assert container.container_id == "container-abc"
        assert container.container_ip == "172.17.0.2"
        assert isinstance(container.created_at, datetime)
        assert isinstance(container.last_active, datetime)

    @pytest.mark.asyncio
    async def test_query_success(self):
        """Test successful query to container."""
        container = AgentContainer("test-123", "container-abc", "172.17.0.2")

        # Create async generator for mock websocket messages
        async def mock_ws_messages():
            yield '{"type": "message", "data": {"content": "Hello"}}'
            yield '{"type": "complete", "status": "success"}'

        # Mock websocket context manager
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.__aiter__ = lambda self: mock_ws_messages()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)

        with patch('websockets.connect', return_value=mock_ws):
            responses = []
            async for response in container.query("Test query"):
                responses.append(response)

        assert len(responses) == 2
        assert responses[0]["type"] == "message"
        assert responses[0]["data"]["content"] == "Hello"
        assert responses[1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_query_error_handling(self):
        """Test query error handling."""
        container = AgentContainer("test-123", "container-abc", "172.17.0.2")

        # Mock websocket connection failure
        with patch('websockets.connect', side_effect=Exception("Connection failed")):
            responses = []
            async for response in container.query("Test query"):
                responses.append(response)

        assert len(responses) == 1
        assert responses[0]["type"] == "error"
        assert "Connection failed" in responses[0]["message"]

    @pytest.mark.asyncio
    async def test_query_updates_last_active(self):
        """Test that query updates last_active timestamp."""
        container = AgentContainer("test-123", "container-abc", "172.17.0.2")
        original_time = container.last_active

        # Wait a bit to ensure time difference
        await asyncio.sleep(0.01)

        # Create async generator for mock websocket messages
        async def mock_ws_messages():
            await asyncio.sleep(0.01)  # Small delay to ensure time passes
            yield '{"type": "message", "data": {"content": "Test"}}'
            yield '{"type": "complete", "status": "success"}'

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: mock_ws_messages()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)

        with patch('websockets.connect', return_value=mock_ws):
            async for _ in container.query("Test"):
                pass

        assert container.last_active > original_time


@pytest.mark.unit
class TestContainerManagerInitialization:
    """Test ContainerManager initialization."""

    def test_lazy_docker_client(self):
        """Test that Docker client is not initialized on __init__."""
        manager = ContainerManager()
        assert manager._docker_client is None

    def test_docker_client_property_initializes(self):
        """Test that accessing docker_client property initializes it."""
        manager = ContainerManager()

        with patch('docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_from_env.return_value = mock_client

            client = manager.docker_client

            assert client == mock_client
            mock_from_env.assert_called_once()

    def test_docker_client_caching(self):
        """Test that docker_client is cached after initialization."""
        manager = ContainerManager()

        with patch('docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_from_env.return_value = mock_client

            # Access multiple times
            client1 = manager.docker_client
            client2 = manager.docker_client

            assert client1 == client2
            mock_from_env.assert_called_once()  # Only called once


@pytest.mark.unit
class TestCreateAgentContainer:
    """Test container creation."""

    @pytest.mark.asyncio
    async def test_create_container_success(self, mock_docker_client):
        """Test successful container creation."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        # Mock wait_for_ready
        with patch.object(manager, '_wait_for_ready', new=AsyncMock()):
            container = await manager.create_agent_container(
                api_key="sk-ant-test-key",
                system_prompt="Test prompt",
                allowed_tools="Bash,Read"
            )

        assert isinstance(container, AgentContainer)
        assert container.container_ip == "172.17.0.2"
        assert container.agent_id in manager.active_containers

        # Verify Docker API calls
        mock_docker_client.containers.run.assert_called_once()
        call_kwargs = mock_docker_client.containers.run.call_args.kwargs

        assert call_kwargs['image'] == "agcluster/agent:latest"
        assert call_kwargs['detach'] is True
        assert call_kwargs['environment']['ANTHROPIC_API_KEY'] == "sk-ant-test-key"
        assert call_kwargs['environment']['SYSTEM_PROMPT'] == "Test prompt"
        assert call_kwargs['environment']['ALLOWED_TOOLS'] == "Bash,Read"

    @pytest.mark.asyncio
    async def test_create_container_with_defaults(self, mock_docker_client):
        """Test container creation with default values."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        with patch.object(manager, '_wait_for_ready', new=AsyncMock()):
            container = await manager.create_agent_container(
                api_key="sk-ant-test-key"
            )

        call_kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert "SYSTEM_PROMPT" in call_kwargs['environment']
        assert "ALLOWED_TOOLS" in call_kwargs['environment']

    @pytest.mark.asyncio
    async def test_create_container_image_not_found(self, mock_docker_client):
        """Test handling when Docker image is not found."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        mock_docker_client.containers.run.side_effect = docker.errors.ImageNotFound("Image not found")

        with pytest.raises(ValueError, match="Agent image not found"):
            await manager.create_agent_container(api_key="test-key")

    @pytest.mark.asyncio
    async def test_create_container_docker_error(self, mock_docker_client):
        """Test handling Docker API errors."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        mock_docker_client.containers.run.side_effect = docker.errors.APIError("Docker error")

        with pytest.raises(RuntimeError, match="Failed to create container"):
            await manager.create_agent_container(api_key="test-key")

    @pytest.mark.asyncio
    async def test_container_security_settings(self, mock_docker_client):
        """Test that containers have proper security settings."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        with patch.object(manager, '_wait_for_ready', new=AsyncMock()):
            await manager.create_agent_container(api_key="test-key")

        call_kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert "no-new-privileges" in call_kwargs['security_opt']
        assert "ALL" in call_kwargs['cap_drop']

    @pytest.mark.asyncio
    async def test_container_resource_limits(self, mock_docker_client):
        """Test that containers have resource limits."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        with patch.object(manager, '_wait_for_ready', new=AsyncMock()):
            await manager.create_agent_container(api_key="test-key")

        call_kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert 'mem_limit' in call_kwargs
        assert 'cpu_quota' in call_kwargs

    @pytest.mark.asyncio
    async def test_container_labels(self, mock_docker_client):
        """Test that containers have proper labels."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        with patch.object(manager, '_wait_for_ready', new=AsyncMock()):
            await manager.create_agent_container(api_key="test-key")

        call_kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert call_kwargs['labels']['agcluster'] == "true"
        assert 'agent_id' in call_kwargs['labels']


@pytest.mark.unit
class TestWaitForReady:
    """Test container readiness detection."""

    @pytest.mark.asyncio
    async def test_wait_for_ready_success(self, mock_docker_client):
        """Test successful wait for container ready."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        mock_container = mock_docker_client.containers.run.return_value
        mock_container.status = "running"
        mock_container.name = "test-container"

        # Mock successful WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)

        with patch('websockets.connect', return_value=mock_ws):
            # Should not raise
            await manager._wait_for_ready(mock_container)

    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self, mock_docker_client):
        """Test timeout when container doesn't become ready."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        mock_container = Mock()
        mock_container.reload = Mock()
        mock_container.status = "created"  # Never becomes running

        with pytest.raises(TimeoutError, match="did not become ready"):
            await manager._wait_for_ready(mock_container, timeout=1)

    @pytest.mark.asyncio
    async def test_wait_for_ready_port_not_open(self, mock_docker_client):
        """Test waiting when port is not immediately open."""
        manager = ContainerManager()

        mock_container = Mock()
        mock_container.reload = Mock()
        mock_container.status = "running"
        mock_container.attrs = {
            "NetworkSettings": {"IPAddress": "172.17.0.2"}
        }

        # Simulate port not open, then timeout
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 1  # Connection refused
            mock_socket_class.return_value = mock_socket

            with pytest.raises(TimeoutError):
                await manager._wait_for_ready(mock_container, timeout=1)


@pytest.mark.unit
class TestStopContainer:
    """Test container stopping and cleanup."""

    @pytest.mark.asyncio
    async def test_stop_container_success(self, mock_docker_client):
        """Test successful container stop."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        # Add container to active containers
        agent_container = AgentContainer("test-123", "container-abc", "172.17.0.2")
        manager.active_containers["test-123"] = agent_container

        mock_container = Mock()
        mock_docker_client.containers.get.return_value = mock_container

        await manager.stop_container("test-123")

        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.remove.assert_called_once()
        assert "test-123" not in manager.active_containers

    @pytest.mark.asyncio
    async def test_stop_nonexistent_container(self, mock_docker_client):
        """Test stopping container that doesn't exist in tracking."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        # Should not raise
        await manager.stop_container("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_container_not_found_in_docker(self, mock_docker_client):
        """Test stopping when container not found in Docker."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        agent_container = AgentContainer("test-123", "container-abc", "172.17.0.2")
        manager.active_containers["test-123"] = agent_container

        mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Not found")

        # Should not raise, should clean up
        await manager.stop_container("test-123")
        assert "test-123" not in manager.active_containers

    @pytest.mark.asyncio
    async def test_stop_container_cleanup_on_error(self, mock_docker_client):
        """Test that container is removed from tracking even on error."""
        manager = ContainerManager()
        manager._docker_client = mock_docker_client

        agent_container = AgentContainer("test-123", "container-abc", "172.17.0.2")
        manager.active_containers["test-123"] = agent_container

        mock_container = Mock()
        mock_container.stop.side_effect = Exception("Stop failed")
        mock_docker_client.containers.get.return_value = mock_container

        # Should not raise
        await manager.stop_container("test-123")
        # Should still be cleaned up
        assert "test-123" not in manager.active_containers


@pytest.mark.unit
class TestContainerLookup:
    """Test container retrieval methods."""

    def test_get_container_exists(self):
        """Test getting existing container."""
        manager = ContainerManager()
        agent_container = AgentContainer("test-123", "container-abc", "172.17.0.2")
        manager.active_containers["test-123"] = agent_container

        result = manager.get_container("test-123")
        assert result == agent_container

    def test_get_container_not_exists(self):
        """Test getting non-existent container."""
        manager = ContainerManager()

        result = manager.get_container("nonexistent")
        assert result is None

    def test_list_containers(self):
        """Test listing all containers."""
        manager = ContainerManager()

        container1 = AgentContainer("test-1", "container-1", "172.17.0.2")
        container2 = AgentContainer("test-2", "container-2", "172.17.0.3")

        manager.active_containers["test-1"] = container1
        manager.active_containers["test-2"] = container2

        containers = manager.list_containers()
        assert len(containers) == 2
        assert container1 in containers
        assert container2 in containers

    def test_list_containers_empty(self):
        """Test listing when no containers exist."""
        manager = ContainerManager()

        containers = manager.list_containers()
        assert containers == []
