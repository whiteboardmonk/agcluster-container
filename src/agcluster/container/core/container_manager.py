"""Container lifecycle management using provider abstraction"""

import logging
import uuid
from typing import Dict, Optional, AsyncIterator
from datetime import datetime, timezone

from agcluster.container.core.config import settings
from agcluster.container.core.providers import ProviderFactory, ProviderConfig, ContainerInfo
from agcluster.container.models.agent_config import AgentConfig

logger = logging.getLogger(__name__)


RESERVED_ENV_VARS = {
    "ANTHROPIC_API_KEY",
    "AGENT_CONFIG_JSON",
    "AGENT_ID",
    "SESSION_ID",
    "CONVERSATION_ID",
}


class AgentContainer:
    """
    Wrapper around ContainerInfo for backward compatibility.

    This class maintains the same interface as the old AgentContainer
    while using the new provider-based ContainerInfo internally.
    """

    def __init__(
        self,
        container_info: ContainerInfo,
        config_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        self.container_info = container_info
        self.agent_id = container_info.metadata.get("agent_id", container_info.container_id[:12])
        self.container_id = container_info.container_id
        self.container_ip = container_info.metadata.get("container_ip", "")
        self.config_id = config_id
        self.config = config
        self.created_at = datetime.now(timezone.utc)
        self.last_active = datetime.now(timezone.utc)

    async def query(self, message: str) -> AsyncIterator:
        """
        Send query to agent via provider and yield responses.

        This method delegates to the provider's execute_query method.
        The actual provider is obtained from the global container manager.
        """
        # Get the provider from the container manager
        from agcluster.container.core.container_manager import container_manager

        try:
            async for response in container_manager.provider.execute_query(
                self.container_info,
                message,
                [],  # Conversation history (TODO: maintain across calls if needed)
            ):
                # Update last active
                self.last_active = datetime.now(timezone.utc)

                # Yield the response
                yield response

                # Stop if complete or error
                if response.get("type") in ["complete", "error"]:
                    break

        except Exception as e:
            logger.error(f"Error querying container {self.agent_id}: {e}")
            yield {"type": "error", "message": f"Container communication error: {str(e)}"}


class ContainerManager:
    """
    Manages containers using provider abstraction.

    This refactored version uses the ProviderFactory to support multiple
    container platforms (Docker, Fly, Cloudflare, Vercel) while maintaining
    the same external API for backward compatibility.
    """

    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize container manager with specified provider.

        Args:
            provider_name: Provider to use (docker, fly_machines, etc.)
                          If None, uses settings.container_provider
        """
        provider_name = provider_name or settings.container_provider

        # Create provider based on name
        try:
            if provider_name == "docker":
                self.provider = ProviderFactory.create_provider(
                    "docker", network_name=settings.docker_network
                )
            elif provider_name == "fly_machines":
                # TODO: Implement when FlyProvider is ready
                logger.warning("Fly Machines provider not yet implemented, falling back to Docker")
                self.provider = ProviderFactory.create_provider(
                    "docker", network_name=settings.docker_network
                )
            elif provider_name == "cloudflare":
                # TODO: Implement when CloudflareProvider is ready
                logger.warning("Cloudflare provider not yet implemented, falling back to Docker")
                self.provider = ProviderFactory.create_provider(
                    "docker", network_name=settings.docker_network
                )
            elif provider_name == "vercel":
                # TODO: Implement when VercelProvider is ready
                logger.warning("Vercel provider not yet implemented, falling back to Docker")
                self.provider = ProviderFactory.create_provider(
                    "docker", network_name=settings.docker_network
                )
            else:
                logger.warning(f"Unknown provider {provider_name}, using docker")
                self.provider = ProviderFactory.create_provider(
                    "docker", network_name=settings.docker_network
                )
        except Exception as e:
            logger.error(f"Error creating provider {provider_name}: {e}, falling back to docker")
            self.provider = ProviderFactory.create_provider(
                "docker", network_name=settings.docker_network
            )

        self.provider_name = provider_name
        self.active_containers: Dict[str, AgentContainer] = {}

        logger.info(f"ContainerManager initialized with {self.provider.__class__.__name__}")

    def _sanitize_mcp_env(
        self, config: AgentConfig, mcp_env: Optional[Dict[str, Dict[str, str]]]
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Validate and sanitize MCP environment variables supplied at launch.

        Only allow variables explicitly declared in each server's config.env and
        block overrides of core container variables. Returns a filtered copy.
        """
        if not mcp_env:
            return None

        if not config.mcp_servers:
            raise ValueError("mcp_env provided but no mcp_servers configured")

        sanitized: Dict[str, Dict[str, str]] = {}

        for server_name, server_env in mcp_env.items():
            if server_name not in config.mcp_servers:
                raise ValueError(f"Unknown MCP server '{server_name}' in mcp_env")

            declared_env = getattr(config.mcp_servers[server_name], "env", {}) or {}
            allowed_keys = set(declared_env.keys())

            if not allowed_keys and server_env:
                raise ValueError(
                    f"MCP server '{server_name}' does not declare env keys; cannot accept runtime credentials"
                )

            sanitized[server_name] = {}
            for key, value in server_env.items():
                if key in RESERVED_ENV_VARS:
                    raise ValueError(f"MCP env key '{key}' is reserved and cannot be overridden")
                if key not in allowed_keys:
                    raise ValueError(
                        f"MCP env key '{key}' not declared in config for server '{server_name}'"
                    )
                sanitized[server_name][key] = value

        return sanitized

    async def create_agent_container_from_config(
        self,
        api_key: str,
        config: AgentConfig,
        config_id: str,
        mcp_env: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> AgentContainer:
        """
        Create agent container from configuration using provider.

        Args:
            api_key: Anthropic API key
            config: Agent configuration
            config_id: Configuration ID (for tracking)
            mcp_env: Optional runtime environment variables for MCP servers

        Returns:
            AgentContainer instance
        """
        session_id = f"session-{uuid.uuid4().hex[:12]}"

        logger.info(f"Creating container for session {session_id} with config {config_id}")

        # Validate and sanitize runtime MCP environment variables
        sanitized_mcp_env = self._sanitize_mcp_env(config, mcp_env)

        # Build provider config
        provider_config = ProviderConfig(
            platform=self.provider_name,
            cpu_quota=(
                config.resource_limits.cpu_quota
                if config.resource_limits
                else settings.container_cpu_quota
            ),
            memory_limit=(
                config.resource_limits.memory_limit
                if config.resource_limits
                else settings.container_memory_limit
            ),
            storage_limit=(
                config.resource_limits.storage_limit
                if config.resource_limits
                else settings.container_storage_limit
            ),
            allowed_tools=config.allowed_tools,
            system_prompt=config.system_prompt,
            max_turns=config.max_turns,
            api_key=api_key,
            platform_credentials={},  # TODO: Add platform-specific creds when needed
            mcp_servers=config.mcp_servers,  # Pass MCP servers from config
            mcp_env=sanitized_mcp_env,  # Pass runtime MCP environment variables
            permission_mode=config.permission_mode or "acceptEdits",
        )

        # Create container via provider
        container_info = await self.provider.create_container(session_id, provider_config)

        # Wrap in AgentContainer for backward compatibility
        agent_container = AgentContainer(
            container_info=container_info, config_id=config_id, config=config
        )

        # Store in active containers
        agent_id = agent_container.agent_id
        self.active_containers[agent_id] = agent_container

        logger.info(f"Container created successfully: {agent_id} at {container_info.endpoint_url}")

        return agent_container

    async def create_agent_container(
        self, api_key: str, system_prompt: Optional[str] = None, allowed_tools: Optional[str] = None
    ) -> AgentContainer:
        """
        Create a new agent container (legacy method for backward compatibility).

        This method is maintained for backward compatibility with existing code.
        New code should use create_agent_container_from_config().

        Args:
            api_key: Anthropic API key
            system_prompt: System prompt for the agent
            allowed_tools: Comma-separated list of allowed tools

        Returns:
            AgentContainer instance
        """
        session_id = f"session-{uuid.uuid4().hex[:12]}"

        logger.info(f"Creating container for session {session_id} (legacy mode)")

        # Build provider config from legacy params
        provider_config = ProviderConfig(
            platform=self.provider_name,
            cpu_quota=settings.container_cpu_quota,
            memory_limit=settings.container_memory_limit,
            storage_limit=settings.container_storage_limit,
            allowed_tools=(allowed_tools or settings.default_allowed_tools).split(","),
            system_prompt=system_prompt or settings.default_system_prompt,
            max_turns=100,  # Default
            api_key=api_key,
            platform_credentials={},
            permission_mode="acceptEdits",
        )

        # Create container via provider
        container_info = await self.provider.create_container(session_id, provider_config)

        # Wrap in AgentContainer
        agent_container = AgentContainer(container_info=container_info)

        # Store in active containers
        agent_id = agent_container.agent_id
        self.active_containers[agent_id] = agent_container

        logger.info(f"Container created successfully: {agent_id}")

        return agent_container

    async def stop_container(self, agent_id: str):
        """
        Stop and remove a container.

        Args:
            agent_id: Agent ID to stop
        """
        if agent_id not in self.active_containers:
            logger.warning(f"Agent {agent_id} not found in active containers")
            return

        agent_container = self.active_containers[agent_id]

        try:
            logger.info(f"Stopping container for agent {agent_id}")

            # Stop via provider
            await self.provider.stop_container(agent_container.container_id)

            logger.info(f"Container for agent {agent_id} stopped")

        except Exception as e:
            logger.error(f"Error stopping container for agent {agent_id}: {e}")
        finally:
            # Remove from active containers
            del self.active_containers[agent_id]

    def get_container(self, agent_id: str) -> Optional[AgentContainer]:
        """
        Get container by agent ID.

        Args:
            agent_id: Agent ID

        Returns:
            AgentContainer instance or None
        """
        return self.active_containers.get(agent_id)

    def list_containers(self):
        """
        List all active containers.

        Returns:
            List of AgentContainer instances
        """
        return list(self.active_containers.values())

    async def cleanup(self):
        """
        Cleanup all active containers and provider resources.
        """
        logger.info(f"Cleaning up container manager ({len(self.active_containers)} active)")

        # Stop all active containers
        for agent_id in list(self.active_containers.keys()):
            try:
                await self.stop_container(agent_id)
            except Exception as e:
                logger.error(f"Error stopping container {agent_id} during cleanup: {e}")

        # Cleanup provider
        try:
            await self.provider.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up provider: {e}")

        logger.info("Container manager cleanup complete")


# Global container manager instance
container_manager = ContainerManager()
