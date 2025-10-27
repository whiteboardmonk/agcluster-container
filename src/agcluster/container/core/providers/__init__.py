"""
Multi-provider container orchestration for AgCluster.

This package provides an abstraction layer for running Claude Agent SDK containers
across multiple platforms (Docker, Fly Machines, Cloudflare, Vercel, etc.).
"""

from .base import ContainerProvider, ContainerInfo, ProviderConfig
from .factory import ProviderFactory
from .docker_provider import DockerProvider
from .fly_provider import FlyProvider

# Register providers
ProviderFactory.register_provider("docker", DockerProvider)
ProviderFactory.register_provider("fly_machines", FlyProvider)

__all__ = [
    "ContainerProvider",
    "ContainerInfo",
    "ProviderConfig",
    "ProviderFactory",
    "DockerProvider",
    "FlyProvider",
]
