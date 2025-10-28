"""Unit tests for provider base classes and data models."""

import pytest
from dataclasses import asdict
from agcluster.container.core.providers.base import ContainerInfo, ProviderConfig, ContainerProvider


@pytest.mark.unit
class TestContainerInfo:
    """Test ContainerInfo dataclass."""

    def test_creation(self):
        """Test creating ContainerInfo instance."""
        info = ContainerInfo(
            container_id="test-123",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"agent_id": "agent-456"},
        )

        assert info.container_id == "test-123"
        assert info.endpoint_url == "http://172.17.0.2:3000"
        assert info.status == "running"
        assert info.platform == "docker"
        assert info.metadata["agent_id"] == "agent-456"

    def test_to_dict(self):
        """Test converting ContainerInfo to dict."""
        info = ContainerInfo(
            container_id="test-123",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={},
        )

        data = asdict(info)
        assert isinstance(data, dict)
        assert data["container_id"] == "test-123"
        assert data["platform"] == "docker"

    def test_metadata_optional(self):
        """Test that metadata can contain arbitrary data."""
        info = ContainerInfo(
            container_id="test-123",
            endpoint_url="http://172.17.0.2:3000",
            status="running",
            platform="docker",
            metadata={"custom_field": "value", "nested": {"data": "here"}, "count": 42},
        )

        assert info.metadata["custom_field"] == "value"
        assert info.metadata["nested"]["data"] == "here"
        assert info.metadata["count"] == 42


@pytest.mark.unit
class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_minimal_config(self):
        """Test creating minimal ProviderConfig."""
        config = ProviderConfig(
            platform="docker",
            cpu_quota=100000,
            memory_limit="2g",
            storage_limit="5g",
            allowed_tools=["Bash", "Read"],
            system_prompt="Test prompt",
            max_turns=50,
            api_key="test-key",
            platform_credentials={},
        )

        assert config.platform == "docker"
        assert config.cpu_quota == 100000
        assert config.memory_limit == "2g"
        assert config.allowed_tools == ["Bash", "Read"]
        assert config.api_key == "test-key"

    def test_full_config(self):
        """Test creating full ProviderConfig with all fields."""
        config = ProviderConfig(
            platform="fly_machines",
            cpu_quota=200000,
            memory_limit="4g",
            storage_limit="10g",
            allowed_tools=["Bash", "Read", "Write", "Grep"],
            system_prompt="You are a helpful AI assistant.",
            max_turns=100,
            api_key="sk-ant-test",
            platform_credentials={"fly_api_token": "fly_token_123", "fly_app_name": "my-app"},
        )

        assert config.platform == "fly_machines"
        assert config.platform_credentials["fly_api_token"] == "fly_token_123"

    def test_resource_limits(self):
        """Test resource limit configurations."""
        config = ProviderConfig(
            platform="docker",
            cpu_quota=400000,  # 4 CPUs
            memory_limit="8g",
            storage_limit="20g",
            allowed_tools=[],
            system_prompt="",
            max_turns=100,
            api_key="test",
            platform_credentials={},
        )

        assert config.cpu_quota == 400000
        assert config.memory_limit == "8g"
        assert config.storage_limit == "20g"

    def test_to_dict(self):
        """Test converting ProviderConfig to dict."""
        config = ProviderConfig(
            platform="docker",
            cpu_quota=100000,
            memory_limit="2g",
            storage_limit="5g",
            allowed_tools=["Bash"],
            system_prompt="Test",
            max_turns=50,
            api_key="key",
            platform_credentials={},
        )

        data = asdict(config)
        assert isinstance(data, dict)
        assert data["platform"] == "docker"
        assert data["max_turns"] == 50


@pytest.mark.unit
class TestContainerProviderInterface:
    """Test ContainerProvider abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ContainerProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ContainerProvider()

    def test_subclass_must_implement_all_methods(self):
        """Test that subclass must implement all abstract methods."""

        class IncompleteProvider(ContainerProvider):
            """Provider missing implementations."""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteProvider()

    def test_valid_subclass_implementation(self):
        """Test that valid subclass can be created."""

        class ValidProvider(ContainerProvider):
            """Minimal valid provider."""

            async def create_container(self, session_id, config):
                return ContainerInfo(
                    container_id="test",
                    endpoint_url="http://test:3000",
                    status="running",
                    platform="test",
                    metadata={},
                )

            async def stop_container(self, container_id):
                return True

            async def get_container_status(self, container_id):
                return "running"

            async def execute_query(self, container_info, query, history):
                yield {"type": "message", "data": {"content": "test"}}

            async def list_containers(self):
                return []

            async def cleanup(self):
                pass

            async def upload_files(self, container_id, files, target_path, overwrite):
                return [f["safe_name"] for f in files]

        # Should not raise
        provider = ValidProvider()
        assert isinstance(provider, ContainerProvider)


@pytest.mark.unit
class TestProviderMethodSignatures:
    """Test that provider methods have correct signatures."""

    class TestProvider(ContainerProvider):
        """Test provider for signature verification."""

        async def create_container(self, session_id: str, config: ProviderConfig) -> ContainerInfo:
            return ContainerInfo(
                container_id=f"container-{session_id}",
                endpoint_url="http://test:3000",
                status="running",
                platform="test",
                metadata={"session_id": session_id},
            )

        async def stop_container(self, container_id: str) -> bool:
            return True

        async def get_container_status(self, container_id: str) -> str:
            return "running"

        async def execute_query(self, container_info: ContainerInfo, query: str, history: list):
            yield {"type": "message", "data": {"content": query}}

        async def list_containers(self) -> list:
            return []

        async def cleanup(self):
            pass

        async def upload_files(
            self, container_id: str, files: list, target_path: str, overwrite: bool
        ) -> list:
            return [f["safe_name"] for f in files]

    @pytest.mark.asyncio
    async def test_create_container_signature(self):
        """Test create_container returns ContainerInfo."""
        provider = self.TestProvider()
        config = ProviderConfig(
            platform="test",
            cpu_quota=100000,
            memory_limit="2g",
            storage_limit="5g",
            allowed_tools=[],
            system_prompt="",
            max_turns=50,
            api_key="test",
            platform_credentials={},
        )

        result = await provider.create_container("session-123", config)
        assert isinstance(result, ContainerInfo)
        assert result.container_id == "container-session-123"

    @pytest.mark.asyncio
    async def test_stop_container_signature(self):
        """Test stop_container returns bool."""
        provider = self.TestProvider()
        result = await provider.stop_container("test-id")
        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_container_status_signature(self):
        """Test get_container_status returns string."""
        provider = self.TestProvider()
        result = await provider.get_container_status("test-id")
        assert isinstance(result, str)
        assert result == "running"

    @pytest.mark.asyncio
    async def test_execute_query_signature(self):
        """Test execute_query returns async iterator."""
        provider = self.TestProvider()
        container_info = ContainerInfo(
            container_id="test",
            endpoint_url="http://test:3000",
            status="running",
            platform="test",
            metadata={},
        )

        messages = []
        async for message in provider.execute_query(container_info, "Hello", []):
            messages.append(message)

        assert len(messages) == 1
        assert messages[0]["type"] == "message"

    @pytest.mark.asyncio
    async def test_list_containers_signature(self):
        """Test list_containers returns list."""
        provider = self.TestProvider()
        result = await provider.list_containers()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_cleanup_signature(self):
        """Test cleanup returns None."""
        provider = self.TestProvider()
        result = await provider.cleanup()
        assert result is None
