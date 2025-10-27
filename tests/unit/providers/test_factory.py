"""Unit tests for ProviderFactory."""

import pytest
from unittest.mock import Mock
from agcluster.container.core.providers.factory import ProviderFactory
from agcluster.container.core.providers.base import ContainerProvider, ContainerInfo, ProviderConfig


@pytest.mark.unit
class TestProviderRegistration:
    """Test provider registration in factory."""

    def setup_method(self):
        """Reset factory state before each test."""
        # Save original providers
        self.original_providers = ProviderFactory._providers.copy()

    def teardown_method(self):
        """Restore original factory state after each test."""
        ProviderFactory._providers = self.original_providers

    def test_register_provider(self):
        """Test registering a new provider."""

        class TestProvider(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("test_provider", TestProvider)

        assert "test_provider" in ProviderFactory._providers
        assert ProviderFactory._providers["test_provider"] == TestProvider

    def test_register_duplicate_provider_overwrites(self):
        """Test that registering duplicate provider overwrites."""

        class Provider1(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        class Provider2(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("test", Provider1)
        ProviderFactory.register_provider("test", Provider2)

        assert ProviderFactory._providers["test"] == Provider2

    def test_docker_provider_pre_registered(self):
        """Test that Docker provider is pre-registered."""
        assert "docker" in ProviderFactory.list_providers()


@pytest.mark.unit
class TestProviderCreation:
    """Test provider creation via factory."""

    def setup_method(self):
        """Reset factory state before each test."""
        self.original_providers = ProviderFactory._providers.copy()

    def teardown_method(self):
        """Restore original factory state after each test."""
        ProviderFactory._providers = self.original_providers

    def test_create_registered_provider(self):
        """Test creating a registered provider."""

        class TestProvider(ContainerProvider):
            def __init__(self, custom_param=None):
                self.custom_param = custom_param

            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("test", TestProvider)

        provider = ProviderFactory.create_provider("test", custom_param="value")

        assert isinstance(provider, TestProvider)
        assert provider.custom_param == "value"

    def test_create_unregistered_provider_raises_error(self):
        """Test that creating unregistered provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider platform: nonexistent"):
            ProviderFactory.create_provider("nonexistent")

    def test_create_provider_with_kwargs(self):
        """Test creating provider with keyword arguments."""

        class ConfigurableProvider(ContainerProvider):
            def __init__(self, option1=None, option2=None):
                self.option1 = option1
                self.option2 = option2

            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("configurable", ConfigurableProvider)

        provider = ProviderFactory.create_provider(
            "configurable",
            option1="value1",
            option2="value2"
        )

        assert provider.option1 == "value1"
        assert provider.option2 == "value2"

    def test_create_docker_provider(self):
        """Test creating Docker provider (should be pre-registered)."""
        provider = ProviderFactory.create_provider("docker")

        assert provider is not None
        assert isinstance(provider, ContainerProvider)


@pytest.mark.unit
class TestProviderListing:
    """Test listing available providers."""

    def setup_method(self):
        """Reset factory state before each test."""
        self.original_providers = ProviderFactory._providers.copy()

    def teardown_method(self):
        """Restore original factory state after each test."""
        ProviderFactory._providers = self.original_providers

    def test_list_providers_returns_list(self):
        """Test that list_providers returns a list."""
        providers = ProviderFactory.list_providers()
        assert isinstance(providers, list)

    def test_list_providers_includes_docker(self):
        """Test that Docker provider is in the list."""
        providers = ProviderFactory.list_providers()
        assert "docker" in providers

    def test_list_providers_after_registration(self):
        """Test listing providers after registering new ones."""

        class Provider1(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        class Provider2(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("provider1", Provider1)
        ProviderFactory.register_provider("provider2", Provider2)

        providers = ProviderFactory.list_providers()

        assert "provider1" in providers
        assert "provider2" in providers

    def test_list_providers_sorted(self):
        """Test that providers are returned in sorted order."""

        class ProviderZ(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        class ProviderA(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        ProviderFactory.register_provider("z_provider", ProviderZ)
        ProviderFactory.register_provider("a_provider", ProviderA)

        providers = ProviderFactory.list_providers()

        # Check if sorted
        assert providers == sorted(providers)


@pytest.mark.unit
class TestProviderAvailability:
    """Test checking provider availability."""

    def setup_method(self):
        """Reset factory state before each test."""
        self.original_providers = ProviderFactory._providers.copy()

    def teardown_method(self):
        """Restore original factory state after each test."""
        ProviderFactory._providers = self.original_providers

    def test_is_provider_available_true(self):
        """Test checking if provider is available."""
        assert ProviderFactory.is_provider_available("docker") is True

    def test_is_provider_available_false(self):
        """Test checking if nonexistent provider is available."""
        assert ProviderFactory.is_provider_available("nonexistent") is False

    def test_is_provider_available_after_registration(self):
        """Test availability check after registration."""

        class TestProvider(ContainerProvider):
            async def create_container(self, session_id, config):
                pass

            async def stop_container(self, container_id):
                pass

            async def get_container_status(self, container_id):
                pass

            async def execute_query(self, container_info, query, history):
                yield {}

            async def list_containers(self):
                pass

            async def cleanup(self):
                pass

        assert ProviderFactory.is_provider_available("new_provider") is False

        ProviderFactory.register_provider("new_provider", TestProvider)

        assert ProviderFactory.is_provider_available("new_provider") is True
