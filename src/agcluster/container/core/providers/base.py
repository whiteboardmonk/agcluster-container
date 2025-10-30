"""
Base classes and interfaces for multi-provider container orchestration.

This module defines the abstract ContainerProvider interface that all platform-specific
providers must implement, along with shared data models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, AsyncIterator


@dataclass
class ContainerInfo:
    """
    Platform-agnostic container information.

    Attributes:
        container_id: Unique identifier for the container/instance
        endpoint_url: HTTP/HTTPS endpoint URL for HTTP/SSE communication
        status: Current status (running, stopped, error, etc.)
        platform: Provider platform name (docker, fly_machines, cloudflare, vercel)
        metadata: Platform-specific additional data
    """

    container_id: str
    endpoint_url: str  # HTTP/SSE endpoint (e.g., http://172.17.0.2:3000 or https://agent.fly.dev)
    status: str
    platform: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """
    Configuration for creating a container on a specific provider.

    Attributes:
        platform: Provider platform name
        cpu_quota: CPU quota in Docker units (100000 = 1 CPU)
        memory_limit: Memory limit (e.g., "4g", "2048m")
        storage_limit: Storage limit (e.g., "10g")
        allowed_tools: List of tools available to agent
        system_prompt: System prompt for the agent
        max_turns: Maximum conversation turns
        api_key: Anthropic API key
        platform_credentials: Platform-specific authentication credentials
        extra_files: Extra files to mount in the container (key: relative path, value: content in bytes)
    """

    platform: str
    cpu_quota: int
    memory_limit: str
    storage_limit: str
    allowed_tools: list[str]
    system_prompt: str
    max_turns: int
    api_key: str
    platform_credentials: Dict[str, Any] = field(default_factory=dict)
    extra_files: Dict[str, bytes] = field(default_factory=dict)


class ContainerProvider(ABC):
    """
    Abstract base class for container providers.

    All platform-specific providers (Docker, Fly, Cloudflare, Vercel) must implement
    this interface to ensure consistent behavior across platforms.

    Communication Protocol: HTTP/SSE
    - All providers must expose an HTTP endpoint that accepts POST requests
    - Responses are streamed via Server-Sent Events (SSE)
    - This ensures universal compatibility across all platforms
    """

    @abstractmethod
    async def create_container(self, session_id: str, config: ProviderConfig) -> ContainerInfo:
        """
        Create and start a new container/instance for the agent.

        Args:
            session_id: Unique session identifier
            config: Provider configuration including resources, tools, and credentials

        Returns:
            ContainerInfo: Information about the created container

        Raises:
            Exception: If container creation fails
        """
        pass

    @abstractmethod
    async def stop_container(self, container_id: str) -> bool:
        """
        Stop and remove a container/instance.

        Args:
            container_id: Container identifier to stop

        Returns:
            bool: True if successfully stopped, False otherwise
        """
        pass

    @abstractmethod
    async def get_container_status(self, container_id: str) -> str:
        """
        Get the current status of a container.

        Args:
            container_id: Container identifier

        Returns:
            str: Status string (running, stopped, error, etc.)
        """
        pass

    @abstractmethod
    async def execute_query(
        self, container_info: ContainerInfo, query: str, conversation_history: list[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a query on the agent container and stream responses via HTTP/SSE.

        This method sends a POST request to the container's HTTP endpoint and
        consumes the Server-Sent Events (SSE) stream.

        Args:
            container_info: Information about the target container
            query: User query to process
            conversation_history: Previous messages in the conversation

        Yields:
            Dict[str, Any]: Streamed response messages from the agent

        Raises:
            Exception: If query execution fails
        """
        pass

    @abstractmethod
    async def list_containers(self) -> list[ContainerInfo]:
        """
        List all active containers managed by this provider.

        Returns:
            list[ContainerInfo]: List of active containers
        """
        pass

    @abstractmethod
    async def upload_files(
        self, container_id: str, files: list[Dict[str, Any]], target_path: str, overwrite: bool
    ) -> list[str]:
        """
        Upload files to a container's workspace.

        Args:
            container_id: Container identifier
            files: List of file dictionaries with keys:
                   - original_name: Original filename
                   - safe_name: Sanitized filename
                   - content: File content as bytes
                   - size: File size in bytes
            target_path: Target directory path (validated)
            overwrite: Whether to overwrite existing files

        Returns:
            list[str]: List of successfully uploaded filenames

        Raises:
            HTTPException: If upload fails or file already exists (when overwrite=False)
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        Cleanup provider resources (connections, clients, etc.).

        Called when the provider is no longer needed.
        """
        pass
