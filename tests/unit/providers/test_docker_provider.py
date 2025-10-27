"""Unit tests for Docker provider implementation."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import docker
import httpx

from agcluster.container.core.providers.docker_provider import DockerProvider
from agcluster.container.core.providers.base import (
    ContainerInfo,
    ProviderConfig,
)


@pytest.fixture
def provider_config():
    """Create a standard provider config for testing."""
    return ProviderConfig(
        platform="docker",
        cpu_quota=200000,
        memory_limit="4g",
        storage_limit="10g",
        allowed_tools=["Bash", "Read", "Write", "Grep"],
        system_prompt="You are a helpful AI assistant.",
        max_turns=100,
        api_key="sk-ant-test-key",
        platform_credentials={}
    )


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = Mock()
    client.containers = Mock()
    return client


@pytest.fixture
def mock_container():
    """Create a mock Docker container."""
    container = Mock()
    container.id = "container-abc123"
    container.status = "running"
    container.attrs = {
        'NetworkSettings': {
            'Networks': {
                'agcluster-container_agcluster-network': {
                    'IPAddress': '172.18.0.5'
                }
            },
            'IPAddress': ''
        }
    }
    container.reload = Mock()
    container.stop = Mock()
    container.remove = Mock()
    return container


@pytest.mark.unit
class TestDockerProviderInitialization:
    """Test DockerProvider initialization."""

    def test_init_with_default_network(self):
        """Test initialization with default network name."""
        provider = DockerProvider()

        assert provider.network_name == "agcluster-container_agcluster-network"
        assert provider._docker_client is None
        assert provider.active_containers == {}

    def test_init_with_custom_network(self):
        """Test initialization with custom network name."""
        provider = DockerProvider(network_name="custom-network")

        assert provider.network_name == "custom-network"
        assert provider._docker_client is None
        assert provider.active_containers == {}

    def test_lazy_docker_client_initialization(self):
        """Test Docker client is lazily initialized."""
        provider = DockerProvider()

        # Client should be None initially
        assert provider._docker_client is None

        # Access property should initialize client
        with patch('docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_from_env.return_value = mock_client

            client = provider.docker_client

            assert client == mock_client
            mock_from_env.assert_called_once()
            assert provider._docker_client == mock_client

    def test_lazy_docker_client_single_initialization(self):
        """Test Docker client is only initialized once."""
        provider = DockerProvider()

        with patch('docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_from_env.return_value = mock_client

            # Access multiple times
            client1 = provider.docker_client
            client2 = provider.docker_client
            client3 = provider.docker_client

            # Should only call from_env once
            mock_from_env.assert_called_once()
            assert client1 == client2 == client3


@pytest.mark.unit
class TestCreateContainer:
    """Test container creation."""

    @pytest.mark.asyncio
    async def test_create_container_success(self, provider_config, mock_container):
        """Test successful container creation."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with patch.object(provider, '_wait_for_health', new_callable=AsyncMock):
            container_info = await provider.create_container(
                session_id="session-123",
                config=provider_config
            )

        # Verify container info
        assert isinstance(container_info, ContainerInfo)
        assert container_info.container_id == "container-abc123"
        assert container_info.endpoint_url == "http://172.18.0.5:3000"
        assert container_info.status == "running"
        assert container_info.platform == "docker"
        assert container_info.metadata["session_id"] == "session-123"
        assert "agent_id" in container_info.metadata

        # Verify container was added to active containers
        assert "session-123" in provider.active_containers

    @pytest.mark.asyncio
    async def test_create_container_docker_api_call(self, provider_config, mock_container):
        """Test Docker API call parameters."""
        provider = DockerProvider(network_name="test-network")

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with patch.object(provider, '_wait_for_health', new_callable=AsyncMock):
            await provider.create_container(
                session_id="session-456",
                config=provider_config
            )

        # Verify Docker API call
        mock_client.containers.run.assert_called_once()
        call_args = mock_client.containers.run.call_args

        # Check image
        assert call_args[1]['image'] == "agcluster/agent:latest"
        assert call_args[1]['detach'] is True

        # Check network
        assert call_args[1]['network'] == "test-network"

        # Check resource limits
        assert call_args[1]['mem_limit'] == "4g"
        assert call_args[1]['cpu_quota'] == 200000

        # Check environment
        env = call_args[1]['environment']
        assert env['ANTHROPIC_API_KEY'] == "sk-ant-test-key"
        assert 'AGENT_CONFIG_JSON' in env

        # Verify agent config JSON
        config_json = json.loads(env['AGENT_CONFIG_JSON'])
        assert config_json['id'] == "docker"
        assert config_json['allowed_tools'] == ["Bash", "Read", "Write", "Grep"]
        assert config_json['system_prompt'] == "You are a helpful AI assistant."
        assert config_json['max_turns'] == 100

        # Check security
        assert call_args[1]['security_opt'] == ["no-new-privileges"]
        assert call_args[1]['cap_drop'] == ["ALL"]

        # Check labels
        labels = call_args[1]['labels']
        assert labels['agcluster'] == "true"
        assert labels['agcluster.session_id'] == "session-456"
        assert labels['agcluster.provider'] == "docker"

    @pytest.mark.asyncio
    async def test_create_container_network_ip_retrieval(self, provider_config):
        """Test container IP retrieval from custom network."""
        provider = DockerProvider()

        mock_container = Mock()
        mock_container.id = "container-xyz"
        mock_container.attrs = {
            'NetworkSettings': {
                'Networks': {
                    'agcluster-container_agcluster-network': {
                        'IPAddress': '172.18.0.10'
                    }
                },
                'IPAddress': ''
            }
        }
        mock_container.reload = Mock()

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with patch.object(provider, '_wait_for_health', new_callable=AsyncMock):
            container_info = await provider.create_container(
                session_id="session-net",
                config=provider_config
            )

        assert container_info.endpoint_url == "http://172.18.0.10:3000"
        assert container_info.metadata["container_ip"] == "172.18.0.10"

    @pytest.mark.asyncio
    async def test_create_container_fallback_ip(self, provider_config):
        """Test IP retrieval falls back to root IPAddress if no networks."""
        provider = DockerProvider()

        mock_container = Mock()
        mock_container.id = "container-fallback"
        mock_container.attrs = {
            'NetworkSettings': {
                'Networks': {},
                'IPAddress': '172.17.0.2'
            }
        }
        mock_container.reload = Mock()

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with patch.object(provider, '_wait_for_health', new_callable=AsyncMock):
            container_info = await provider.create_container(
                session_id="session-fallback",
                config=provider_config
            )

        assert container_info.endpoint_url == "http://172.17.0.2:3000"

    @pytest.mark.asyncio
    async def test_create_container_no_ip_raises_error(self, provider_config):
        """Test error when container has no IP address."""
        provider = DockerProvider()

        mock_container = Mock()
        mock_container.id = "container-no-ip"
        mock_container.attrs = {
            'NetworkSettings': {
                'Networks': {},
                'IPAddress': ''
            }
        }
        mock_container.reload = Mock()

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with pytest.raises(RuntimeError, match="Failed to get container IP address"):
            await provider.create_container(
                session_id="session-no-ip",
                config=provider_config
            )

    @pytest.mark.asyncio
    async def test_create_container_image_not_found(self, provider_config):
        """Test error when Docker image not found."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.run.side_effect = docker.errors.ImageNotFound("image not found")
        provider._docker_client = mock_client

        with pytest.raises(ValueError, match="Agent image not found: agcluster/agent:latest"):
            await provider.create_container(
                session_id="session-no-image",
                config=provider_config
            )

    @pytest.mark.asyncio
    async def test_create_container_docker_api_error(self, provider_config):
        """Test error when Docker API fails."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.run.side_effect = docker.errors.APIError("API error")
        provider._docker_client = mock_client

        with pytest.raises(RuntimeError, match="Failed to create container"):
            await provider.create_container(
                session_id="session-api-error",
                config=provider_config
            )

    @pytest.mark.asyncio
    async def test_create_container_health_check_timeout(self, provider_config, mock_container):
        """Test container creation continues when health check times out."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        provider._docker_client = mock_client

        with patch.object(provider, '_wait_for_health', new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = TimeoutError("Health check timeout")

            # Should not raise exception, just log warning
            container_info = await provider.create_container(
                session_id="session-health-timeout",
                config=provider_config
            )

        # Container should still be created
        assert container_info.container_id == "container-abc123"


@pytest.mark.unit
class TestStopContainer:
    """Test container stopping."""

    @pytest.mark.asyncio
    async def test_stop_container_success(self, mock_container):
        """Test successful container stop."""
        provider = DockerProvider()

        # Add container to active containers
        provider.active_containers["session-123"] = ContainerInfo(
            container_id="container-abc123",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={"session_id": "session-123"}
        )

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        provider._docker_client = mock_client

        result = await provider.stop_container("container-abc123")

        assert result is True
        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.remove.assert_called_once()

        # Verify container removed from active containers
        assert "session-123" not in provider.active_containers

    @pytest.mark.asyncio
    async def test_stop_container_not_found(self):
        """Test stopping non-existent container."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        provider._docker_client = mock_client

        result = await provider.stop_container("container-not-found")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_container_general_error(self, mock_container):
        """Test error handling when stopping container fails."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_container.stop.side_effect = Exception("Stop failed")
        provider._docker_client = mock_client

        result = await provider.stop_container("container-error")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_container_removes_from_active_list(self, mock_container):
        """Test container is removed from active containers on stop."""
        provider = DockerProvider()

        # Add multiple containers
        provider.active_containers["session-1"] = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={}
        )
        provider.active_containers["session-2"] = ContainerInfo(
            container_id="container-2",
            endpoint_url="http://172.18.0.6:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_container.id = "container-1"
        provider._docker_client = mock_client

        await provider.stop_container("container-1")

        # Only container-1 should be removed
        assert "session-1" not in provider.active_containers
        assert "session-2" in provider.active_containers


@pytest.mark.unit
class TestGetContainerStatus:
    """Test getting container status."""

    @pytest.mark.asyncio
    async def test_get_container_status_running(self):
        """Test getting status of running container."""
        provider = DockerProvider()

        mock_container = Mock()
        mock_container.status = "running"
        mock_container.reload = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        provider._docker_client = mock_client

        status = await provider.get_container_status("container-123")

        assert status == "running"
        mock_container.reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_container_status_stopped(self):
        """Test getting status of stopped container."""
        provider = DockerProvider()

        mock_container = Mock()
        mock_container.status = "exited"
        mock_container.reload = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        provider._docker_client = mock_client

        status = await provider.get_container_status("container-stopped")

        assert status == "exited"

    @pytest.mark.asyncio
    async def test_get_container_status_not_found(self):
        """Test getting status of non-existent container."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        provider._docker_client = mock_client

        status = await provider.get_container_status("container-not-found")

        assert status == "not_found"

    @pytest.mark.asyncio
    async def test_get_container_status_error(self):
        """Test error handling when getting status."""
        provider = DockerProvider()

        mock_client = Mock()
        mock_client.containers.get.side_effect = Exception("API error")
        provider._docker_client = mock_client

        status = await provider.get_container_status("container-error")

        assert status == "error"


@pytest.mark.unit
class TestExecuteQuery:
    """Test query execution via HTTP/SSE."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """Test successful query execution."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-123",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        # Mock HTTP response with SSE data
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "data: {\"type\": \"message\", \"content\": \"Hello\"}"
            yield "data: {\"type\": \"message\", \"content\": \"World\"}"
            yield "data: {\"type\": \"complete\", \"status\": \"success\"}"

        mock_response.aiter_lines = mock_aiter_lines

        # Create proper async context manager mock
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="Hello",
                conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 3
        assert messages[0]["type"] == "message"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "World"
        assert messages[2]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_execute_query_with_history(self):
        """Test query execution with conversation history."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-456",
            endpoint_url="http://172.18.0.6:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        conversation_history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"}
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "data: {\"type\": \"message\", \"content\": \"Response\"}"

        mock_response.aiter_lines = mock_aiter_lines

        # Create proper async context manager mock
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="New query",
                conversation_history=conversation_history
            ):
                messages.append(message)

        # Verify POST request was made with history
        mock_client.stream.assert_called_once()
        call_args = mock_client.stream.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "http://172.18.0.6:3000/query"
        assert call_args[1]["json"]["query"] == "New query"
        assert call_args[1]["json"]["history"] == conversation_history

    @pytest.mark.asyncio
    async def test_execute_query_http_error(self):
        """Test handling of HTTP errors during query."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-error",
            endpoint_url="http://172.18.0.7:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_error_response = Mock()
        mock_error_response.status_code = 500

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_error_response
        ))

        async def mock_aiter_lines():
            # This won't be called due to raise_for_status
            yield ""

        mock_response.aiter_lines = mock_aiter_lines

        # Create proper async context manager mock
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="Test",
                conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 1
        assert messages[0]["type"] == "error"
        assert "HTTP error" in messages[0]["message"]
        assert "500" in messages[0]["message"]

    @pytest.mark.asyncio
    async def test_execute_query_connection_error(self):
        """Test handling of connection errors."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-conn-error",
            endpoint_url="http://172.18.0.8:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_client = MagicMock()
        mock_client.stream = Mock(side_effect=httpx.RequestError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="Test",
                conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 1
        assert messages[0]["type"] == "error"
        assert "Request error" in messages[0]["message"]

    @pytest.mark.asyncio
    async def test_execute_query_invalid_json(self):
        """Test handling of invalid JSON in SSE stream."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-json-error",
            endpoint_url="http://172.18.0.9:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield "data: {\"type\": \"message\", \"content\": \"Valid\"}"
            yield "data: invalid json {{"
            yield "data: {\"type\": \"message\", \"content\": \"Also valid\"}"

        mock_response.aiter_lines = mock_aiter_lines

        # Create proper async context manager mock
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="Test",
                conversation_history=[]
            ):
                messages.append(message)

        # Should skip invalid JSON and continue
        assert len(messages) == 2
        assert messages[0]["content"] == "Valid"
        assert messages[1]["content"] == "Also valid"

    @pytest.mark.asyncio
    async def test_execute_query_unexpected_error(self):
        """Test handling of unexpected errors."""
        provider = DockerProvider()

        container_info = ContainerInfo(
            container_id="container-unexpected",
            endpoint_url="http://172.18.0.10:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_client = MagicMock()
        mock_client.stream = Mock(side_effect=Exception("Unexpected error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            messages = []
            async for message in provider.execute_query(
                container_info=container_info,
                query="Test",
                conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 1
        assert messages[0]["type"] == "error"
        assert "Unexpected error" in messages[0]["message"]


@pytest.mark.unit
class TestListContainers:
    """Test listing containers."""

    @pytest.mark.asyncio
    async def test_list_containers_empty(self):
        """Test listing when no containers are active."""
        provider = DockerProvider()

        containers = await provider.list_containers()

        assert isinstance(containers, list)
        assert len(containers) == 0

    @pytest.mark.asyncio
    async def test_list_containers_with_active(self):
        """Test listing active containers."""
        provider = DockerProvider()

        # Add containers to active list
        provider.active_containers["session-1"] = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "agent-1"}
        )
        provider.active_containers["session-2"] = ContainerInfo(
            container_id="container-2",
            endpoint_url="http://172.18.0.6:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "agent-2"}
        )

        containers = await provider.list_containers()

        assert len(containers) == 2
        assert all(isinstance(c, ContainerInfo) for c in containers)

        # Verify both containers are present
        container_ids = [c.container_id for c in containers]
        assert "container-1" in container_ids
        assert "container-2" in container_ids

    @pytest.mark.asyncio
    async def test_list_containers_returns_copy(self):
        """Test that list_containers returns container values."""
        provider = DockerProvider()

        provider.active_containers["session-1"] = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        containers1 = await provider.list_containers()
        containers2 = await provider.list_containers()

        # Should return list values from dict
        assert containers1[0].container_id == containers2[0].container_id


@pytest.mark.unit
class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_no_containers(self):
        """Test cleanup when no containers are active."""
        provider = DockerProvider()

        mock_client = Mock()
        provider._docker_client = mock_client

        await provider.cleanup()

        # Docker client should be closed
        mock_client.close.assert_called_once()
        assert provider._docker_client is None

    @pytest.mark.asyncio
    async def test_cleanup_stops_all_containers(self, mock_container):
        """Test cleanup stops all active containers."""
        provider = DockerProvider()

        # Add multiple containers
        provider.active_containers["session-1"] = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={}
        )
        provider.active_containers["session-2"] = ContainerInfo(
            container_id="container-2",
            endpoint_url="http://172.18.0.6:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        provider._docker_client = mock_client

        await provider.cleanup()

        # Should have called stop_container for each
        assert mock_client.containers.get.call_count == 2
        assert mock_container.stop.call_count == 2
        assert mock_container.remove.call_count == 2

        # Should close Docker client
        mock_client.close.assert_called_once()
        assert provider._docker_client is None

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors(self, mock_container):
        """Test cleanup continues even if some containers fail."""
        provider = DockerProvider()

        provider.active_containers["session-1"] = ContainerInfo(
            container_id="container-1",
            endpoint_url="http://172.18.0.5:3000",
            status="running",
            platform="docker",
            metadata={}
        )
        provider.active_containers["session-2"] = ContainerInfo(
            container_id="container-2",
            endpoint_url="http://172.18.0.6:3000",
            status="running",
            platform="docker",
            metadata={}
        )

        mock_client = Mock()
        # First call fails, second succeeds
        mock_client.containers.get.side_effect = [
            Exception("Stop failed"),
            mock_container
        ]
        provider._docker_client = mock_client

        await provider.cleanup()

        # Should have attempted both
        assert mock_client.containers.get.call_count == 2
        # Should still close client
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_closes_docker_client(self):
        """Test cleanup closes Docker client."""
        provider = DockerProvider()

        with patch('docker.from_env') as mock_from_env:
            mock_client = Mock()
            mock_from_env.return_value = mock_client

            # Initialize client
            _ = provider.docker_client

            await provider.cleanup()

            mock_client.close.assert_called_once()
            assert provider._docker_client is None


@pytest.mark.unit
class TestWaitForHealth:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_wait_for_health_success(self):
        """Test successful health check."""
        provider = DockerProvider()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await provider._wait_for_health("http://172.18.0.5:3000", timeout=5)

        # Should have called health endpoint
        mock_client.get.assert_called()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == "http://172.18.0.5:3000/health"

    @pytest.mark.asyncio
    async def test_wait_for_health_retry_until_success(self):
        """Test health check retries until success."""
        provider = DockerProvider()

        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"status": "healthy"}

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[
            httpx.RequestError("Connection refused"),
            mock_response_success
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await provider._wait_for_health("http://172.18.0.5:3000", timeout=5)

        # Should have called multiple times
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_health_timeout(self):
        """Test health check timeout."""
        provider = DockerProvider()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Use very short timeout
            with pytest.raises(TimeoutError, match="did not become healthy within"):
                await provider._wait_for_health("http://172.18.0.5:3000", timeout=1)

    @pytest.mark.asyncio
    async def test_wait_for_health_unhealthy_status(self):
        """Test health check with unhealthy status."""
        provider = DockerProvider()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "unhealthy"}

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Should timeout because status is not "healthy"
            with pytest.raises(TimeoutError):
                await provider._wait_for_health("http://172.18.0.5:3000", timeout=1)

    @pytest.mark.asyncio
    async def test_wait_for_health_non_200_status(self):
        """Test health check with non-200 HTTP status."""
        provider = DockerProvider()

        mock_response = Mock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_response
        ))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Should timeout because health check keeps failing
            with pytest.raises(TimeoutError):
                await provider._wait_for_health("http://172.18.0.5:3000", timeout=1)
