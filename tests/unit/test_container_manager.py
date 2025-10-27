"""Unit tests for ContainerManager with provider abstraction."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import asyncio

from agcluster.container.core.container_manager import (
    ContainerManager,
    AgentContainer,
)
from agcluster.container.core.providers import ContainerInfo, ProviderConfig


@pytest.mark.unit
class TestAgentContainer:
    """Test AgentContainer class."""

    def test_initialization(self):
        """Test AgentContainer initialization."""
        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        container = AgentContainer(
            container_info=container_info,
            config_id="test-config",
            config=None
        )

        assert container.agent_id == "test-123"
        assert container.container_id == "container-abc"
        assert container.container_ip == "172.17.0.2"
        assert container.config_id == "test-config"
        assert isinstance(container.created_at, datetime)
        assert isinstance(container.last_active, datetime)

    @pytest.mark.asyncio
    async def test_query_success(self):
        """Test successful query to container via provider."""
        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        container = AgentContainer(container_info=container_info)

        # Mock the provider.execute_query method
        async def mock_execute_query(container_info, message, history):
            yield {"type": "message", "data": {"content": "Hello"}}
            yield {"type": "complete", "status": "success"}

        with patch('agcluster.container.core.container_manager.container_manager') as mock_mgr:
            mock_mgr.provider.execute_query = mock_execute_query

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
        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        container = AgentContainer(container_info=container_info)

        # Mock provider error - must be async generator
        async def mock_execute_query_error(container_info, message, history):
            raise Exception("Connection failed")
            yield  # This line makes it an async generator (never reached)

        with patch('agcluster.container.core.container_manager.container_manager') as mock_mgr:
            mock_mgr.provider.execute_query = mock_execute_query_error

            responses = []
            async for response in container.query("Test query"):
                responses.append(response)

        assert len(responses) == 1
        assert responses[0]["type"] == "error"
        assert "Connection failed" in responses[0]["message"]

    @pytest.mark.asyncio
    async def test_query_updates_last_active(self):
        """Test that query updates last_active timestamp."""
        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        container = AgentContainer(container_info=container_info)
        original_time = container.last_active

        # Wait a bit to ensure time difference
        await asyncio.sleep(0.01)

        async def mock_execute_query(container_info, message, history):
            await asyncio.sleep(0.01)  # Small delay to ensure time passes
            yield {"type": "message", "data": {"content": "Test"}}
            yield {"type": "complete", "status": "success"}

        with patch('agcluster.container.core.container_manager.container_manager') as mock_mgr:
            mock_mgr.provider.execute_query = mock_execute_query

            async for _ in container.query("Test"):
                pass

        assert container.last_active > original_time


@pytest.mark.unit
class TestContainerManagerInitialization:
    """Test ContainerManager initialization with providers."""

    def test_default_provider(self):
        """Test that ContainerManager initializes with default provider."""
        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider') as mock_create:
            mock_provider = Mock()
            mock_create.return_value = mock_provider

            manager = ContainerManager()

            assert manager.provider == mock_provider
            mock_create.assert_called_once()

    def test_specific_provider(self):
        """Test initializing with specific provider."""
        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider') as mock_create:
            mock_provider = Mock()
            mock_create.return_value = mock_provider

            manager = ContainerManager(provider_name="fly_machines")

            # Should still use docker as fallback since fly_machines not implemented
            assert manager.provider == mock_provider


@pytest.mark.unit
class TestCreateAgentContainer:
    """Test container creation via provider."""

    @pytest.mark.asyncio
    async def test_create_container_success(self):
        """Test successful container creation via provider."""
        mock_provider = Mock()

        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "agent-123", "container_ip": "172.17.0.2"}
        )

        mock_provider.create_container = AsyncMock(return_value=container_info)

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider', return_value=mock_provider):
            manager = ContainerManager()

            container = await manager.create_agent_container(
                api_key="sk-ant-test-key",
                system_prompt="Test prompt",
                allowed_tools="Bash,Read"
            )

        assert isinstance(container, AgentContainer)
        assert container.container_ip == "172.17.0.2"
        assert container.agent_id in manager.active_containers

        # Verify provider was called
        mock_provider.create_container.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_container_from_config(self):
        """Test container creation from config."""
        from agcluster.container.models.agent_config import AgentConfig

        mock_provider = Mock()

        container_info = ContainerInfo(
            container_id="container-xyz",
            endpoint_url="http://172.17.0.3:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "agent-456", "container_ip": "172.17.0.3"}
        )

        mock_provider.create_container = AsyncMock(return_value=container_info)

        config = AgentConfig(
            id="test-config",
            name="Test Config",
            allowed_tools=["Bash", "Read", "Write"]
        )

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider', return_value=mock_provider):
            manager = ContainerManager()

            container = await manager.create_agent_container_from_config(
                api_key="sk-ant-test-key",
                config=config,
                config_id="test-config"
            )

        assert isinstance(container, AgentContainer)
        assert container.config_id == "test-config"
        assert container.config == config
        mock_provider.create_container.assert_called_once()


@pytest.mark.unit
class TestStopContainer:
    """Test container stopping via provider."""

    @pytest.mark.asyncio
    async def test_stop_container_success(self):
        """Test successful container stop."""
        mock_provider = Mock()
        mock_provider.stop_container = AsyncMock(return_value=True)

        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider', return_value=mock_provider):
            manager = ContainerManager()

            # Add container to active containers
            agent_container = AgentContainer(container_info=container_info)
            manager.active_containers["test-123"] = agent_container

            await manager.stop_container("test-123")

        mock_provider.stop_container.assert_called_once_with("container-abc")
        assert "test-123" not in manager.active_containers

    @pytest.mark.asyncio
    async def test_stop_nonexistent_container(self):
        """Test stopping container that doesn't exist in tracking."""
        mock_provider = Mock()

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider', return_value=mock_provider):
            manager = ContainerManager()

            # Should not raise
            await manager.stop_container("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_container_cleanup_on_error(self):
        """Test that container is removed from tracking even on error."""
        mock_provider = Mock()
        mock_provider.stop_container = AsyncMock(side_effect=Exception("Stop failed"))

        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider', return_value=mock_provider):
            manager = ContainerManager()

            agent_container = AgentContainer(container_info=container_info)
            manager.active_containers["test-123"] = agent_container

            # Should not raise
            await manager.stop_container("test-123")
            # Should still be cleaned up
            assert "test-123" not in manager.active_containers


@pytest.mark.unit
class TestContainerLookup:
    """Test container retrieval methods."""

    def test_get_container_exists(self):
        """Test getting existing container."""
        container_info = ContainerInfo(
            container_id="container-abc",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-123", "container_ip": "172.17.0.2"}
        )

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider'):
            manager = ContainerManager()
            agent_container = AgentContainer(container_info=container_info)
            manager.active_containers["test-123"] = agent_container

            result = manager.get_container("test-123")
            assert result == agent_container

    def test_get_container_not_exists(self):
        """Test getting non-existent container."""
        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider'):
            manager = ContainerManager()

            result = manager.get_container("nonexistent")
            assert result is None

    def test_list_containers(self):
        """Test listing all containers."""
        container_info1 = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-1", "container_ip": "172.17.0.2"}
        )

        container_info2 = ContainerInfo(
            container_id="container-2",
            endpoint_url="http://172.17.0.3:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "test-2", "container_ip": "172.17.0.3"}
        )

        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider'):
            manager = ContainerManager()

            container1 = AgentContainer(container_info=container_info1)
            container2 = AgentContainer(container_info=container_info2)

            manager.active_containers["test-1"] = container1
            manager.active_containers["test-2"] = container2

            containers = manager.list_containers()
            assert len(containers) == 2
            assert container1 in containers
            assert container2 in containers

    def test_list_containers_empty(self):
        """Test listing when no containers exist."""
        with patch('agcluster.container.core.container_manager.ProviderFactory.create_provider'):
            manager = ContainerManager()

            containers = manager.list_containers()
            assert containers == []
