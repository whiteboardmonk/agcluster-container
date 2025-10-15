"""Docker container lifecycle management for Claude agents"""

import docker
import logging
import uuid
import asyncio
import websockets
import json
from typing import Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

from agcluster.container.core.config import settings
from agcluster.container.models.agent_config import AgentConfig

logger = logging.getLogger(__name__)


class AgentContainer:
    """Represents a Claude SDK agent container"""

    def __init__(
        self,
        agent_id: str,
        container_id: str,
        container_ip: str,
        config_id: Optional[str] = None,
        config: Optional[AgentConfig] = None
    ):
        self.agent_id = agent_id
        self.container_id = container_id
        self.container_ip = container_ip
        self.config_id = config_id
        self.config = config
        self.created_at = datetime.now(timezone.utc)
        self.last_active = datetime.now(timezone.utc)

    async def query(self, message: str):
        """Send query to Claude SDK via WebSocket and yield responses"""
        ws_url = f"ws://{self.container_ip}:8765"

        try:
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=30
            ) as ws:
                # Send query
                await ws.send(json.dumps({
                    "type": "query",
                    "content": message
                }))

                # Stream responses
                async for response in ws:
                    data = json.loads(response)
                    yield data

                    # Update last active
                    self.last_active = datetime.now(timezone.utc)

                    # Stop if complete
                    if data.get("type") in ["complete", "error"]:
                        break

        except Exception as e:
            logger.error(f"Error querying container {self.agent_id}: {e}")
            yield {
                "type": "error",
                "message": f"Container communication error: {str(e)}"
            }


class ContainerManager:
    """Manages Docker containers for Claude agents"""

    def __init__(self):
        self._docker_client = None
        self.active_containers: Dict[str, AgentContainer] = {}

    @property
    def docker_client(self):
        """Lazy initialization of Docker client"""
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    def _prepare_config_mount(self, agent_id: str, config: AgentConfig) -> tuple[str, dict]:
        """
        Prepare config file and volume mount specification

        Args:
            agent_id: Agent ID
            config: Agent configuration

        Returns:
            tuple: (config_file_path, volume_mount_dict)
        """
        # Create config directory
        config_dir = Path("/tmp/agcluster/configs")
        config_dir.mkdir(parents=True, exist_ok=True)

        # Write config to file
        config_path = config_dir / f"{agent_id}.json"
        with open(config_path, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)

        logger.debug(f"Config written to {config_path}")

        # Prepare volume mount
        volume_mount = {
            str(config_path): {
                'bind': '/config/agent-config.json',
                'mode': 'ro'  # Read-only
            }
        }

        return str(config_path), volume_mount

    async def create_agent_container_from_config(
        self,
        api_key: str,
        config: AgentConfig,
        config_id: str
    ) -> AgentContainer:
        """
        Create agent container from configuration

        Args:
            api_key: Anthropic API key
            config: Agent configuration
            config_id: Configuration ID (for tracking)

        Returns:
            AgentContainer instance
        """
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        container_name = f"agcluster-{agent_id}"

        logger.info(f"Creating container for agent {agent_id} with config {config_id}")

        try:
            # Prepare config mount
            config_path, config_mount = self._prepare_config_mount(agent_id, config)

            # Prepare volumes (workspace + config)
            volumes = {
                f"agcluster-workspace-{agent_id}": {
                    'bind': '/workspace',
                    'mode': 'rw'
                }
            }
            volumes.update(config_mount)

            # Environment variables
            env = {
                "AGENT_ID": agent_id,
                "ANTHROPIC_API_KEY": api_key,
                "CONFIG_PATH": "/config/agent-config.json"
            }

            # Resource limits from config
            cpu_quota = None
            mem_limit = None
            if config.resource_limits:
                cpu_quota = config.resource_limits.cpu_quota
                mem_limit = config.resource_limits.memory_limit

            # Create container
            container = self.docker_client.containers.run(
                image=settings.agent_image,
                name=container_name,
                detach=True,

                # Environment
                environment=env,

                # Network
                network=settings.docker_network,

                # Resource limits (from config or defaults)
                mem_limit=mem_limit or settings.container_memory_limit,
                cpu_quota=cpu_quota or settings.container_cpu_quota,

                # Security
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],

                # Volumes (workspace + config)
                volumes=volumes,

                # Labels
                labels={
                    "agcluster": "true",
                    "agent_id": agent_id,
                    "config_id": config_id
                }
            )

            # Wait for container to be ready
            await self._wait_for_ready(container)

            # Get container IP
            container.reload()
            networks = container.attrs['NetworkSettings']['Networks']
            if networks:
                container_ip = list(networks.values())[0]['IPAddress']
            else:
                container_ip = container.attrs['NetworkSettings']['IPAddress']

            # Create agent container object with config
            agent_container = AgentContainer(
                agent_id=agent_id,
                container_id=container.id,
                container_ip=container_ip,
                config_id=config_id,
                config=config
            )
            self.active_containers[agent_id] = agent_container

            logger.info(f"Container {container_name} created successfully at {container_ip}")

            return agent_container

        except docker.errors.ImageNotFound:
            logger.error(f"Docker image {settings.agent_image} not found")
            raise ValueError(f"Agent image not found: {settings.agent_image}")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error creating container: {e}")
            raise RuntimeError(f"Failed to create container: {str(e)}")

    async def create_agent_container(
        self,
        api_key: str,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[str] = None
    ) -> AgentContainer:
        """
        Create a new agent container (legacy method for backward compatibility)

        Note: This method is maintained for backward compatibility.
        New code should use create_agent_container_from_config()
        """

        agent_id = str(uuid.uuid4())[:8]
        container_name = f"agcluster-{agent_id}"

        logger.info(f"Creating container for agent {agent_id} (legacy mode)")

        try:
            # Prepare environment
            env = {
                "AGENT_ID": agent_id,
                "ANTHROPIC_API_KEY": api_key,
                "SYSTEM_PROMPT": system_prompt or settings.default_system_prompt,
                "ALLOWED_TOOLS": allowed_tools or settings.default_allowed_tools
            }

            # Create container
            container = self.docker_client.containers.run(
                image=settings.agent_image,
                name=container_name,
                detach=True,

                # Environment
                environment=env,

                # Network
                network=settings.docker_network,

                # Resource limits
                mem_limit=settings.container_memory_limit,
                cpu_quota=settings.container_cpu_quota,

                # Security
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],

                # Volume for workspace
                volumes={
                    f"agcluster-workspace-{agent_id}": {
                        'bind': '/workspace',
                        'mode': 'rw'
                    }
                },

                # Labels
                labels={
                    "agcluster": "true",
                    "agent_id": agent_id
                }
            )

            # Wait for container to be ready
            await self._wait_for_ready(container)

            # Get container IP
            container.reload()
            networks = container.attrs['NetworkSettings']['Networks']
            if networks:
                container_ip = list(networks.values())[0]['IPAddress']
            else:
                container_ip = container.attrs['NetworkSettings']['IPAddress']

            # Create agent container object
            agent_container = AgentContainer(agent_id, container.id, container_ip)
            self.active_containers[agent_id] = agent_container

            logger.info(f"Container {container_name} created successfully at {container_ip}")

            return agent_container

        except docker.errors.ImageNotFound:
            logger.error(f"Docker image {settings.agent_image} not found")
            raise ValueError(f"Agent image not found: {settings.agent_image}")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error creating container: {e}")
            raise RuntimeError(f"Failed to create container: {str(e)}")

    async def _wait_for_ready(self, container, timeout: int = 30):
        """Wait for container to be ready with adaptive WebSocket check"""
        start_time = datetime.now(timezone.utc)
        container_ip = None

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            try:
                # Reload container info
                container.reload()

                # Check if container is running
                if container.status != "running":
                    await asyncio.sleep(0.5)
                    continue

                # Get container IP (from custom network)
                networks = container.attrs['NetworkSettings']['Networks']
                if networks:
                    container_ip = list(networks.values())[0]['IPAddress']
                else:
                    container_ip = container.attrs['NetworkSettings']['IPAddress']

                if not container_ip:
                    await asyncio.sleep(0.5)
                    continue

                # Try to connect to WebSocket to verify server is ready
                try:
                    logger.debug(f"Container {container.name} at {container_ip}, checking WebSocket...")
                    async with websockets.connect(
                        f"ws://{container_ip}:8765",
                        open_timeout=2,
                        close_timeout=1
                    ) as ws:
                        # Connection successful - server is ready!
                        logger.info(f"Container {container.name} WebSocket ready at {container_ip}")
                        return
                except (OSError, websockets.exceptions.WebSocketException) as e:
                    # Server not ready yet, keep waiting
                    logger.debug(f"WebSocket not ready yet: {e}")
                    await asyncio.sleep(0.5)
                    continue

            except Exception as e:
                logger.debug(f"Waiting for container: {e}")

            await asyncio.sleep(0.5)

        raise TimeoutError(f"Container did not become ready within {timeout}s")

    async def stop_container(self, agent_id: str):
        """Stop and remove a container"""
        if agent_id not in self.active_containers:
            logger.warning(f"Agent {agent_id} not found in active containers")
            return

        agent_container = self.active_containers[agent_id]

        try:
            container = self.docker_client.containers.get(agent_container.container_id)
            logger.info(f"Stopping container for agent {agent_id}")

            container.stop(timeout=10)
            container.remove()

            logger.info(f"Container for agent {agent_id} removed")

        except docker.errors.NotFound:
            logger.warning(f"Container {agent_container.container_id} not found")
        except Exception as e:
            logger.error(f"Error stopping container for agent {agent_id}: {e}")
        finally:
            del self.active_containers[agent_id]

    def get_container(self, agent_id: str) -> Optional[AgentContainer]:
        """Get container by agent ID"""
        return self.active_containers.get(agent_id)

    def list_containers(self):
        """List all active containers"""
        return list(self.active_containers.values())


# Global container manager instance
container_manager = ContainerManager()
