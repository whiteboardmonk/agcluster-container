"""
Factory for creating container provider instances.

This module implements the factory pattern for instantiating platform-specific
container providers based on configuration.
"""

from typing import Dict, Type, Any
from .base import ContainerProvider


class ProviderFactory:
    """
    Factory class for creating container provider instances.

    Supports registration of custom providers and dynamic provider selection
    based on platform name.
    """

    _providers: Dict[str, Type[ContainerProvider]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[ContainerProvider]):
        """
        Register a new provider class.

        Args:
            name: Provider name (e.g., "docker", "fly_machines")
            provider_class: Provider class that implements ContainerProvider

        Raises:
            TypeError: If provider_class doesn't implement ContainerProvider
        """
        if not issubclass(provider_class, ContainerProvider):
            raise TypeError(
                f"Provider class must implement ContainerProvider, got {provider_class}"
            )
        cls._providers[name] = provider_class

    @classmethod
    def create_provider(cls, platform: str, **kwargs: Any) -> ContainerProvider:
        """
        Create a provider instance for the specified platform.

        Args:
            platform: Platform name (docker, fly_machines, cloudflare, vercel)
            **kwargs: Platform-specific initialization arguments

        Returns:
            ContainerProvider: Instantiated provider

        Raises:
            ValueError: If platform is unknown

        Example:
            >>> provider = ProviderFactory.create_provider("docker")
            >>> provider = ProviderFactory.create_provider(
            ...     "fly_machines",
            ...     api_token="xxx",
            ...     app_name="agcluster"
            ... )
        """
        if platform not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider platform: {platform}. " f"Available providers: {available}"
            )

        provider_class = cls._providers[platform]
        return provider_class(**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered provider names in sorted order.

        Returns:
            list[str]: Names of all registered providers, sorted alphabetically
        """
        return sorted(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, platform: str) -> bool:
        """
        Check if a provider is registered.

        Args:
            platform: Platform name to check

        Returns:
            bool: True if provider is registered, False otherwise
        """
        return platform in cls._providers
