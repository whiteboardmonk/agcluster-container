"""Unit tests for Fly Machines provider implementation."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import httpx

from agcluster.container.core.providers.fly_provider import FlyProvider
from agcluster.container.core.providers.base import (
    ContainerInfo,
    ProviderConfig,
)


@pytest.fixture
def provider_config():
    """Create a standard provider config for testing."""
    return ProviderConfig(
        platform="fly_machines",
        cpu_quota=200000,  # 2 CPUs
        memory_limit="4g",
        storage_limit="10g",
        allowed_tools=["Bash", "Read", "Write", "Grep"],
        system_prompt="You are a helpful AI assistant.",
        max_turns=100,
        api_key="sk-ant-test-key",
        platform_credentials={"fly_region": "iad"},
    )


@pytest.fixture
def fly_provider():
    """Create a Fly provider instance."""
    return FlyProvider(
        api_token="test_fly_token",
        app_name="test-app",
        region="iad",
        image="registry.fly.io/agcluster-agent:latest",
    )


@pytest.mark.unit
class TestFlyProviderInitialization:
    """Test FlyProvider initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        provider = FlyProvider(api_token="token123", app_name="my-app")

        assert provider.api_token == "token123"
        assert provider.app_name == "my-app"
        assert provider.region == "iad"
        assert provider.image == "registry.fly.io/agcluster-agent:latest"
        assert provider.base_url == "https://api.machines.dev/v1"
        assert provider.active_machines == {}

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        provider = FlyProvider(
            api_token="custom_token",
            app_name="custom-app",
            region="sjc",
            image="registry.fly.io/custom:v2",
            base_url="https://custom.api.dev/v1",
        )

        assert provider.api_token == "custom_token"
        assert provider.app_name == "custom-app"
        assert provider.region == "sjc"
        assert provider.image == "registry.fly.io/custom:v2"
        assert provider.base_url == "https://custom.api.dev/v1"

    def test_get_headers(self, fly_provider):
        """Test HTTP headers generation."""
        headers = fly_provider._get_headers()

        assert headers["Authorization"] == "Bearer test_fly_token"
        assert headers["Content-Type"] == "application/json"


@pytest.mark.unit
class TestCreateContainer:
    """Test Fly Machine creation."""

    @pytest.mark.asyncio
    async def test_create_machine_success(self, fly_provider, provider_config):
        """Test successful machine creation."""
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "id": "machine-abc123",
            "name": "agcluster-agent-xyz",
            "state": "created",
            "region": "iad",
        }

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-abc123",
            "state": "started",
            "private_ip": "fdaa:0:1da6:a7b:7b:6f9a:c582:2",
            "region": "iad",
        }

        async def mock_post(url, **kwargs):
            return mock_create_response

        async def mock_get(url, **kwargs):
            return mock_info_response

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with patch.object(fly_provider, "_wait_for_health", new_callable=AsyncMock):
                    container_info = await fly_provider.create_container(
                        session_id="session-123", config=provider_config
                    )

        # Verify container info
        assert isinstance(container_info, ContainerInfo)
        assert container_info.container_id == "machine-abc123"
        assert container_info.endpoint_url == "http://[fdaa:0:1da6:a7b:7b:6f9a:c582:2]:3000"
        assert container_info.status == "running"
        assert container_info.platform == "fly_machines"
        assert container_info.metadata["session_id"] == "session-123"
        assert container_info.metadata["app_name"] == "test-app"
        assert container_info.metadata["region"] == "iad"

        # Verify machine was added to active list
        assert "session-123" in fly_provider.active_machines

    @pytest.mark.asyncio
    async def test_create_machine_api_call_parameters(self, fly_provider, provider_config):
        """Test Fly API call parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "machine-456", "state": "created"}

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-456",
            "state": "started",
            "private_ip": "fdaa:0:1da6::1",
            "region": "iad",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_info_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with patch.object(fly_provider, "_wait_for_health", new_callable=AsyncMock):
                    await fly_provider.create_container(
                        session_id="session-456", config=provider_config
                    )

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Check URL
        assert "apps/test-app/machines" in call_args[0][0]

        # Check request body
        machine_config = call_args[1]["json"]
        assert "agcluster-agent-" in machine_config["name"]
        assert machine_config["config"]["image"] == "registry.fly.io/agcluster-agent:latest"
        assert machine_config["config"]["guest"]["cpus"] == 2
        assert machine_config["config"]["guest"]["memory_mb"] == 4096
        assert machine_config["region"] == "iad"

        # Check environment
        env = machine_config["config"]["env"]
        assert env["ANTHROPIC_API_KEY"] == "sk-ant-test-key"
        assert "AGENT_CONFIG_JSON" in env

        # Verify agent config
        config_json = json.loads(env["AGENT_CONFIG_JSON"])
        assert config_json["allowed_tools"] == ["Bash", "Read", "Write", "Grep"]
        assert config_json["system_prompt"] == "You are a helpful AI assistant."
        assert config_json["max_turns"] == 100

    @pytest.mark.asyncio
    async def test_create_machine_custom_region(self, fly_provider):
        """Test machine creation with custom region from credentials."""
        config = ProviderConfig(
            platform="fly_machines",
            cpu_quota=100000,
            memory_limit="2g",
            storage_limit="5g",
            allowed_tools=["Bash"],
            system_prompt="Test",
            max_turns=50,
            api_key="test-key",
            platform_credentials={"fly_region": "sjc"},
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "machine-custom", "state": "created"}

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-custom",
            "state": "started",
            "private_ip": "fdaa::1",
            "region": "sjc",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_info_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with patch.object(fly_provider, "_wait_for_health", new_callable=AsyncMock):
                    await fly_provider.create_container(session_id="session-region", config=config)

        # Verify region
        call_args = mock_client.post.call_args
        machine_config = call_args[1]["json"]
        assert machine_config["region"] == "sjc"

    @pytest.mark.asyncio
    async def test_create_machine_cpu_conversion(self, fly_provider):
        """Test CPU quota conversion."""
        config = ProviderConfig(
            platform="fly_machines",
            cpu_quota=400000,  # 4 CPUs
            memory_limit="8g",
            storage_limit="20g",
            allowed_tools=["Bash"],
            system_prompt="Test",
            max_turns=100,
            api_key="test-key",
            platform_credentials={},
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "machine-cpu", "state": "created"}

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-cpu",
            "state": "started",
            "private_ip": "fdaa::2",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_info_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with patch.object(fly_provider, "_wait_for_health", new_callable=AsyncMock):
                    await fly_provider.create_container("session-cpu", config)

        call_args = mock_client.post.call_args
        machine_config = call_args[1]["json"]
        assert machine_config["config"]["guest"]["cpus"] == 4

    @pytest.mark.asyncio
    async def test_create_machine_memory_conversion(self, fly_provider):
        """Test memory limit conversion."""
        test_cases = [
            ("4g", 4096),
            ("2048m", 2048),
            ("1gb", 1024),
            ("512mb", 512),
        ]

        for memory_limit, expected_mb in test_cases:
            config = ProviderConfig(
                platform="fly_machines",
                cpu_quota=100000,
                memory_limit=memory_limit,
                storage_limit="10g",
                allowed_tools=["Bash"],
                system_prompt="Test",
                max_turns=100,
                api_key="test-key",
                platform_credentials={},
            )

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "machine-mem", "state": "created"}

            mock_info_response = Mock()
            mock_info_response.status_code = 200
            mock_info_response.json.return_value = {
                "id": "machine-mem",
                "state": "started",
                "private_ip": "fdaa::3",
            }

            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=mock_info_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                    with patch.object(fly_provider, "_wait_for_health", new_callable=AsyncMock):
                        await fly_provider.create_container(f"session-{memory_limit}", config)

            call_args = mock_client.post.call_args
            machine_config = call_args[1]["json"]
            assert machine_config["config"]["guest"]["memory_mb"] == expected_mb

    @pytest.mark.asyncio
    async def test_create_machine_invalid_token(self, fly_provider, provider_config):
        """Test error with invalid API token."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Invalid Fly API token"):
                await fly_provider.create_container("session-401", provider_config)

    @pytest.mark.asyncio
    async def test_create_machine_app_not_found(self, fly_provider, provider_config):
        """Test error when Fly app doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "App not found"

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Fly app 'test-app' not found"):
                await fly_provider.create_container("session-404", provider_config)

    @pytest.mark.asyncio
    async def test_create_machine_api_error(self, fly_provider, provider_config):
        """Test error with Fly API failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Fly API error \\(500\\)"):
                await fly_provider.create_container("session-500", provider_config)

    @pytest.mark.asyncio
    async def test_create_machine_no_private_ip(self, fly_provider, provider_config):
        """Test error when machine has no private IP."""
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {"id": "machine-no-ip", "state": "created"}

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-no-ip",
            "state": "started",
            "private_ip": None,
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_create_response)
        mock_client.get = AsyncMock(return_value=mock_info_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Failed to get private IP"):
                    await fly_provider.create_container("session-no-ip", provider_config)

    @pytest.mark.asyncio
    async def test_create_machine_health_check_timeout(self, fly_provider, provider_config):
        """Test machine creation continues when health check times out."""
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {"id": "machine-health", "state": "created"}

        mock_info_response = Mock()
        mock_info_response.status_code = 200
        mock_info_response.json.return_value = {
            "id": "machine-health",
            "state": "started",
            "private_ip": "fdaa::4",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_create_response)
        mock_client.get = AsyncMock(return_value=mock_info_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch.object(fly_provider, "_wait_for_machine_state", new_callable=AsyncMock):
                with patch.object(
                    fly_provider, "_wait_for_health", new_callable=AsyncMock
                ) as mock_health:
                    mock_health.side_effect = TimeoutError("Health check timeout")

                    # Should not raise, just log warning
                    container_info = await fly_provider.create_container(
                        "session-health", provider_config
                    )

        assert container_info.container_id == "machine-health"


@pytest.mark.unit
class TestStopContainer:
    """Test stopping Fly Machines."""

    @pytest.mark.asyncio
    async def test_stop_machine_success(self, fly_provider):
        """Test successful machine stop and destroy."""
        fly_provider.active_machines["session-123"] = ContainerInfo(
            container_id="machine-abc",
            endpoint_url="http://[fdaa::1]:3000",
            status="running",
            platform="fly_machines",
            metadata={"session_id": "session-123"},
        )

        mock_stop_response = Mock()
        mock_stop_response.status_code = 200

        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.raise_for_status = Mock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_stop_response)
        mock_client.delete = AsyncMock(return_value=mock_delete_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fly_provider.stop_container("machine-abc")

        assert result is True
        # Verify machine removed from active list
        assert "session-123" not in fly_provider.active_machines

    @pytest.mark.asyncio
    async def test_stop_machine_not_found(self, fly_provider):
        """Test stopping non-existent machine."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("Not Found", request=Mock(), response=mock_response)
        )

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fly_provider.stop_container("machine-not-found")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_machine_api_error(self, fly_provider):
        """Test error handling when stop fails."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Internal Error", request=Mock(), response=mock_response
            )
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=Mock(status_code=200))
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fly_provider.stop_container("machine-error")

        assert result is False


@pytest.mark.unit
class TestGetContainerStatus:
    """Test getting Fly Machine status."""

    @pytest.mark.asyncio
    async def test_get_status_started(self, fly_provider):
        """Test getting status of started machine."""
        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = {"state": "started", "id": "machine-123"}

            status = await fly_provider.get_container_status("machine-123")

        assert status == "started"

    @pytest.mark.asyncio
    async def test_get_status_stopped(self, fly_provider):
        """Test getting status of stopped machine."""
        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = {"state": "stopped", "id": "machine-456"}

            status = await fly_provider.get_container_status("machine-456")

        assert status == "stopped"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, fly_provider):
        """Test getting status of non-existent machine."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )

            status = await fly_provider.get_container_status("machine-not-found")

        assert status == "not_found"

    @pytest.mark.asyncio
    async def test_get_status_error(self, fly_provider):
        """Test error handling when getting status."""
        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.side_effect = Exception("API error")

            status = await fly_provider.get_container_status("machine-error")

        assert status == "error"


@pytest.mark.unit
class TestExecuteQuery:
    """Test query execution via HTTP/SSE."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, fly_provider):
        """Test successful query execution."""
        container_info = ContainerInfo(
            container_id="machine-123",
            endpoint_url="http://[fdaa::5]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        async def mock_aiter_lines():
            yield 'data: {"type": "message", "content": "Hello"}'
            yield 'data: {"type": "message", "content": "World"}'
            yield 'data: {"type": "complete", "status": "success"}'

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            messages = []
            async for message in fly_provider.execute_query(
                container_info=container_info, query="Test query", conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 3
        assert messages[0]["type"] == "message"
        assert messages[0]["content"] == "Hello"
        assert messages[2]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_execute_query_http_error(self, fly_provider):
        """Test handling of HTTP errors."""
        container_info = ContainerInfo(
            container_id="machine-error",
            endpoint_url="http://[fdaa::6]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )

        mock_error_response = Mock()
        mock_error_response.status_code = 500

        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Internal Error", request=Mock(), response=mock_error_response
            )
        )

        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = Mock(return_value=mock_stream)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            messages = []
            async for message in fly_provider.execute_query(
                container_info=container_info, query="Test", conversation_history=[]
            ):
                messages.append(message)

        assert len(messages) == 1
        assert messages[0]["type"] == "error"
        assert "HTTP error" in messages[0]["message"]


@pytest.mark.unit
class TestListContainers:
    """Test listing Fly Machines."""

    @pytest.mark.asyncio
    async def test_list_containers_empty(self, fly_provider):
        """Test listing when no machines are active."""
        containers = await fly_provider.list_containers()

        assert isinstance(containers, list)
        assert len(containers) == 0

    @pytest.mark.asyncio
    async def test_list_containers_with_active(self, fly_provider):
        """Test listing active machines."""
        fly_provider.active_machines["session-1"] = ContainerInfo(
            container_id="machine-1",
            endpoint_url="http://[fdaa::1]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )
        fly_provider.active_machines["session-2"] = ContainerInfo(
            container_id="machine-2",
            endpoint_url="http://[fdaa::2]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )

        containers = await fly_provider.list_containers()

        assert len(containers) == 2
        assert all(isinstance(c, ContainerInfo) for c in containers)


@pytest.mark.unit
class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_stops_all_machines(self, fly_provider):
        """Test cleanup stops all active machines."""
        fly_provider.active_machines["session-1"] = ContainerInfo(
            container_id="machine-1",
            endpoint_url="http://[fdaa::1]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )
        fly_provider.active_machines["session-2"] = ContainerInfo(
            container_id="machine-2",
            endpoint_url="http://[fdaa::2]:3000",
            status="running",
            platform="fly_machines",
            metadata={},
        )

        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.raise_for_status = Mock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=Mock(status_code=200))
        mock_client.delete = AsyncMock(return_value=mock_delete_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await fly_provider.cleanup()

        # Should have deleted both machines
        assert mock_client.delete.call_count == 2


@pytest.mark.unit
class TestHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_wait_for_machine_state_success(self, fly_provider):
        """Test waiting for machine state."""
        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = {"state": "started", "id": "machine-123"}

            await fly_provider._wait_for_machine_state("machine-123", "started", timeout=5)

        mock_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_machine_state_timeout(self, fly_provider):
        """Test timeout when waiting for machine state."""
        with patch.object(fly_provider, "_get_machine_info", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = {"state": "created", "id": "machine-456"}

            with pytest.raises(TimeoutError, match="did not reach state"):
                await fly_provider._wait_for_machine_state(
                    "machine-456", "started", timeout=1, check_interval=0.3
                )

    @pytest.mark.asyncio
    async def test_parse_memory_limit(self, fly_provider):
        """Test memory limit parsing."""
        test_cases = [
            ("4g", 4096),
            ("4gb", 4096),
            ("2048m", 2048),
            ("2048mb", 2048),
            ("1024k", 1),
            ("1048576", 1),  # bytes
        ]

        for input_str, expected_mb in test_cases:
            result = fly_provider._parse_memory_limit(input_str)
            assert result == expected_mb, f"Failed for input: {input_str}"

    def test_parse_memory_limit_invalid(self, fly_provider):
        """Test invalid memory limit format."""
        with pytest.raises(ValueError, match="Invalid memory limit format"):
            fly_provider._parse_memory_limit("invalid")
