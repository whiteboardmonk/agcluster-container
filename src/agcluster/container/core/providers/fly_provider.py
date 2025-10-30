"""Fly Machines provider implementation using HTTP/SSE communication"""

import asyncio
import httpx
import json
import logging
import uuid
from typing import Dict, Any, AsyncIterator
from datetime import datetime, timezone
from fastapi import HTTPException

from .base import ContainerProvider, ContainerInfo, ProviderConfig

logger = logging.getLogger(__name__)


class FlyProvider(ContainerProvider):
    """
    Fly Machines-based container provider.

    Uses Fly.io Machines API to create and manage ephemeral containers.
    Communication with agent containers via HTTP/SSE over IPv6 private network.

    Fly Machines API Documentation: https://fly.io/docs/machines/api/
    """

    def __init__(
        self,
        api_token: str,
        app_name: str,
        region: str = "iad",
        image: str = "registry.fly.io/agcluster-agent:latest",
        base_url: str = "https://api.machines.dev/v1",
    ):
        """
        Initialize Fly provider.

        Args:
            api_token: Fly.io API token (from `flyctl auth token`)
            app_name: Fly app name (must exist, created via `flyctl apps create`)
            region: Fly region code (default: iad - Ashburn, Virginia)
            image: Docker image in Fly registry
            base_url: Fly Machines API base URL
        """
        self.api_token = api_token
        self.app_name = app_name
        self.region = region
        self.image = image
        self.base_url = base_url.rstrip("/")
        self.active_machines: Dict[str, ContainerInfo] = {}

        logger.info(f"Initialized Fly provider: app={app_name}, region={region}, image={image}")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Fly API requests"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def create_container(self, session_id: str, config: ProviderConfig) -> ContainerInfo:
        """
        Create a new Fly Machine for the agent.

        Args:
            session_id: Unique session identifier
            config: Provider configuration

        Returns:
            ContainerInfo: Information about the created machine

        Raises:
            ValueError: If image not found or app doesn't exist
            RuntimeError: If machine creation fails
        """
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        machine_name = f"agcluster-{agent_id}"

        logger.info(f"Creating Fly Machine for session {session_id}, agent {agent_id}")

        # Convert CPU quota to Fly Machine CPU count (100000 = 1 CPU)
        cpu_count = max(1, config.cpu_quota // 100000)

        # Convert memory limit to MB (e.g., "4g" -> 4096)
        memory_mb = self._parse_memory_limit(config.memory_limit)

        # Build agent config JSON with MCP servers if configured
        agent_config_dict = {
            "id": config.platform,
            "name": f"Agent {agent_id}",
            "allowed_tools": config.allowed_tools,
            "system_prompt": config.system_prompt,
            "permission_mode": "acceptEdits",
            "max_turns": config.max_turns,
        }

        # Add MCP servers if configured
        if config.mcp_servers:
            # Convert Pydantic models to dicts for JSON serialization
            mcp_servers_dict = {}
            for server_name, server_config in config.mcp_servers.items():
                if hasattr(server_config, "model_dump"):
                    # Pydantic v2
                    mcp_servers_dict[server_name] = server_config.model_dump(exclude_none=True)
                elif hasattr(server_config, "dict"):
                    # Pydantic v1
                    mcp_servers_dict[server_name] = server_config.dict(exclude_none=True)
                else:
                    # Already a dict
                    mcp_servers_dict[server_name] = server_config

            agent_config_dict["mcp_servers"] = mcp_servers_dict
            logger.info(f"Added {len(config.mcp_servers)} MCP server(s) to agent config")

        # Prepare environment variables
        env = {
            "AGENT_ID": agent_id,
            "ANTHROPIC_API_KEY": config.api_key,
            "AGENT_CONFIG_JSON": json.dumps(agent_config_dict),
        }

        # Merge MCP environment variables if provided
        if config.mcp_env:
            for server_name, server_env in config.mcp_env.items():
                for env_key, env_value in server_env.items():
                    env[env_key] = env_value
                    logger.info(f"Added MCP env var {env_key} for server {server_name}")

        # Also check for environment variable substitution in MCP server configs
        if config.mcp_servers:
            for server_name, server_config in config.mcp_servers.items():
                # Convert to dict if it's a Pydantic model
                server_dict = server_config
                if hasattr(server_config, "model_dump"):
                    server_dict = server_config.model_dump(exclude_none=True)
                elif hasattr(server_config, "dict"):
                    server_dict = server_config.dict(exclude_none=True)

                if "env" in server_dict:
                    for env_key, env_value in server_dict["env"].items():
                        # If value starts with ${, check if it's already in env
                        # Otherwise use the literal value
                        if isinstance(env_value, str) and env_value.startswith("${"):
                            # Skip - will be resolved at runtime
                            pass
                        else:
                            # Use literal value from config
                            if env_key not in env:
                                env[env_key] = env_value

        # Build machine configuration
        machine_config = {
            "name": machine_name,
            "config": {
                "image": self.image,
                "env": env,
                "services": [
                    {
                        "ports": [
                            {
                                "port": 3000,
                                "handlers": ["http"],
                            }
                        ],
                        "protocol": "tcp",
                        "internal_port": 3000,
                    }
                ],
                "guest": {
                    "cpus": cpu_count,
                    "memory_mb": memory_mb,
                },
                "restart": {"policy": "no"},  # Don't restart on failure (ephemeral)
                "auto_destroy": False,  # We'll destroy manually
            },
            "region": config.platform_credentials.get("fly_region", self.region),
        }

        try:
            # Create machine via Fly API
            url = f"{self.base_url}/apps/{self.app_name}/machines"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json=machine_config,
                    headers=self._get_headers(),
                )

                if response.status_code == 401:
                    raise ValueError("Invalid Fly API token")
                elif response.status_code == 404:
                    raise ValueError(
                        f"Fly app '{self.app_name}' not found. "
                        f"Create it with: flyctl apps create {self.app_name}"
                    )
                elif response.status_code >= 400:
                    error_detail = response.text
                    raise RuntimeError(f"Fly API error ({response.status_code}): {error_detail}")

                response.raise_for_status()
                machine_data = response.json()

            machine_id = machine_data["id"]
            logger.info(f"Machine {machine_id} created, waiting for ready state...")

            # Wait for machine to be in "started" state
            await self._wait_for_machine_state(machine_id, "started", timeout=60)

            # Get machine details to retrieve private IP
            machine_info = await self._get_machine_info(machine_id)
            private_ip = machine_info.get("private_ip")

            if not private_ip:
                raise RuntimeError(f"Failed to get private IP for machine {machine_id}")

            # Build endpoint URL (IPv6 private network)
            # Fly uses IPv6, format: http://[fdaa:...]:3000
            endpoint_url = f"http://[{private_ip}]:3000"

            # Wait for HTTP health check
            try:
                await self._wait_for_health(endpoint_url, timeout=30)
            except TimeoutError:
                logger.warning(
                    f"Health check timed out for machine {machine_id}, " f"but machine is running"
                )

            # Create container info
            container_info = ContainerInfo(
                container_id=machine_id,
                endpoint_url=endpoint_url,
                status="running",
                platform="fly_machines",
                metadata={
                    "machine_name": machine_name,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "private_ip": private_ip,
                    "region": machine_info.get("region", self.region),
                    "app_name": self.app_name,
                },
            )

            self.active_machines[session_id] = container_info
            logger.info(f"Machine {machine_name} created successfully at {endpoint_url}")

            return container_info

        except httpx.RequestError as e:
            logger.error(f"Request error creating Fly Machine: {e}")
            raise RuntimeError(f"Failed to create machine: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating Fly Machine: {e}")
            raise

    async def stop_container(self, container_id: str) -> bool:
        """
        Stop and destroy a Fly Machine.

        Args:
            container_id: Machine ID to stop

        Returns:
            bool: True if successfully stopped and destroyed
        """
        try:
            logger.info(f"Stopping and destroying Fly Machine {container_id}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, try to stop the machine
                stop_url = f"{self.base_url}/apps/{self.app_name}/machines/{container_id}/stop"
                try:
                    await client.post(stop_url, headers=self._get_headers())
                    logger.debug(f"Machine {container_id} stopped")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 404:
                        logger.warning(f"Error stopping machine: {e}")

                # Wait a moment for graceful shutdown
                await asyncio.sleep(1)

                # Delete the machine
                delete_url = f"{self.base_url}/apps/{self.app_name}/machines/{container_id}"
                response = await client.delete(delete_url, headers=self._get_headers())

                if response.status_code == 404:
                    logger.warning(f"Machine {container_id} not found")
                    return False

                response.raise_for_status()

            # Remove from active machines
            session_id = None
            for sid, info in list(self.active_machines.items()):
                if info.container_id == container_id:
                    session_id = sid
                    break

            if session_id:
                del self.active_machines[session_id]

            logger.info(f"Machine {container_id} stopped and destroyed")
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Machine {container_id} not found")
                return False
            logger.error(f"HTTP error stopping machine {container_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error stopping machine {container_id}: {e}")
            return False

    async def get_container_status(self, container_id: str) -> str:
        """
        Get the current status of a Fly Machine.

        Args:
            container_id: Machine ID

        Returns:
            str: Status (started, stopped, destroyed, created, error, not_found)
        """
        try:
            machine_info = await self._get_machine_info(container_id)
            return machine_info.get("state", "unknown")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "not_found"
            logger.error(f"Error getting machine status: {e}")
            return "error"
        except Exception as e:
            logger.error(f"Error getting machine status: {e}")
            return "error"

    async def execute_query(
        self,
        container_info: ContainerInfo,
        query: str,
        conversation_history: list[Dict[str, Any]],
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute query via HTTP/SSE to Fly Machine.

        Args:
            container_info: Container information with endpoint URL
            query: User query
            conversation_history: Conversation history

        Yields:
            Dict[str, Any]: Streamed response messages
        """
        url = f"{container_info.endpoint_url}/query"

        logger.debug(f"Sending query to Fly Machine at {url}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    json={"query": query, "history": conversation_history},
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            try:
                                message = json.loads(data)
                                yield message
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse SSE data: {e}")
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error querying Fly Machine: {e}")
            yield {
                "type": "error",
                "message": f"HTTP error: {e.response.status_code}",
            }
        except httpx.RequestError as e:
            logger.error(f"Request error querying Fly Machine: {e}")
            yield {"type": "error", "message": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error querying Fly Machine: {e}")
            yield {"type": "error", "message": f"Unexpected error: {str(e)}"}

    async def upload_files(
        self, container_id: str, files: list[Dict[str, Any]], target_path: str, overwrite: bool
    ) -> list[str]:
        """
        Upload files to a Fly Machine using HTTP proxy.

        Args:
            container_id: Machine ID
            files: List of file dictionaries
            target_path: Target directory path
            overwrite: Whether to overwrite existing files

        Returns:
            list[str]: List of successfully uploaded filenames

        Raises:
            HTTPException: If upload fails
        """
        # Find container info
        container_info = None
        for info in self.active_machines.values():
            if info.container_id == container_id:
                container_info = info
                break

        if not container_info:
            raise HTTPException(status_code=404, detail=f"Machine {container_id} not found")

        url = f"{container_info.endpoint_url}/upload"

        try:
            # Prepare multipart form data
            form_data = httpx._multipart.MultipartStream(
                data={"target_path": target_path, "overwrite": str(overwrite).lower()},
                files=[
                    ("files", (file_info["safe_name"], file_info["content"])) for file_info in files
                ],
            )

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url, content=form_data, headers={"Content-Type": form_data.content_type}
                )

                if response.status_code == 409:
                    # File already exists
                    raise HTTPException(
                        status_code=409, detail=response.json().get("detail", "File already exists")
                    )

                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"Uploaded {len(result['uploaded'])} files to Fly Machine {container_id}:{target_path}"
                )

                return result["uploaded"]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise HTTPException(
                    status_code=409, detail=e.response.json().get("detail", "File already exists")
                )
            logger.error(f"HTTP error uploading files to Fly Machine {container_id}: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Failed to upload files: {e.response.text}",
            )
        except httpx.RequestError as e:
            logger.error(f"Request error uploading files to Fly Machine {container_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")
        except Exception as e:
            logger.error(f"Error uploading files to Fly Machine {container_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

    async def list_containers(self) -> list[ContainerInfo]:
        """
        List all active Fly Machines.

        Returns:
            list[ContainerInfo]: List of active machines
        """
        return list(self.active_machines.values())

    async def cleanup(self):
        """
        Cleanup Fly provider resources.

        Stops and destroys all active machines.
        """
        logger.info(f"Cleaning up Fly provider ({len(self.active_machines)} active machines)")

        # Stop all active machines
        for session_id, container_info in list(self.active_machines.items()):
            try:
                await self.stop_container(container_info.container_id)
            except Exception as e:
                logger.error(f"Error stopping machine {container_info.container_id}: {e}")

        logger.info("Fly provider cleanup complete")

    # Helper methods

    async def _get_machine_info(self, machine_id: str) -> Dict[str, Any]:
        """
        Get machine information from Fly API.

        Args:
            machine_id: Machine ID

        Returns:
            Dict[str, Any]: Machine information

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def _wait_for_machine_state(
        self,
        machine_id: str,
        target_state: str,
        timeout: int = 60,
        check_interval: float = 1.0,
    ):
        """
        Wait for machine to reach a specific state.

        Args:
            machine_id: Machine ID
            target_state: Target state (e.g., "started", "stopped")
            timeout: Timeout in seconds
            check_interval: Interval between checks in seconds

        Raises:
            TimeoutError: If machine doesn't reach target state within timeout
        """
        start_time = datetime.now(timezone.utc)

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            try:
                machine_info = await self._get_machine_info(machine_id)
                current_state = machine_info.get("state")

                if current_state == target_state:
                    logger.info(f"Machine {machine_id} reached state '{target_state}'")
                    return

                logger.debug(
                    f"Machine {machine_id} state: {current_state}, "
                    f"waiting for {target_state}..."
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Machine {machine_id} not found")
                    raise
                logger.warning(f"Error checking machine state: {e}")

            await asyncio.sleep(check_interval)

        raise TimeoutError(
            f"Machine {machine_id} did not reach state '{target_state}' " f"within {timeout}s"
        )

    async def _wait_for_health(
        self, endpoint_url: str, timeout: int = 30, check_interval: float = 1.0
    ):
        """
        Wait for machine HTTP health endpoint to respond.

        Args:
            endpoint_url: Base URL of machine (with IPv6)
            timeout: Timeout in seconds
            check_interval: Interval between checks in seconds

        Raises:
            TimeoutError: If health check doesn't succeed within timeout
        """
        health_url = f"{endpoint_url}/health"
        start_time = datetime.now(timezone.utc)

        async with httpx.AsyncClient() as client:
            while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
                try:
                    response = await client.get(health_url, timeout=2.0)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            logger.info(f"Machine health check passed at {endpoint_url}")
                            return
                except (httpx.RequestError, httpx.HTTPStatusError):
                    # Server not ready yet
                    await asyncio.sleep(check_interval)
                    continue

                await asyncio.sleep(check_interval)

        raise TimeoutError(f"Machine did not become healthy within {timeout}s at {endpoint_url}")

    def _parse_memory_limit(self, memory_limit: str) -> int:
        """
        Parse memory limit string to MB.

        Args:
            memory_limit: Memory limit (e.g., "4g", "2048m", "512mb")

        Returns:
            int: Memory in MB

        Raises:
            ValueError: If format is invalid
        """
        memory_limit = memory_limit.lower().strip()

        # Extract number and unit
        if memory_limit.endswith("gb") or memory_limit.endswith("g"):
            value = float(memory_limit.rstrip("gb"))
            return int(value * 1024)
        elif memory_limit.endswith("mb") or memory_limit.endswith("m"):
            value = float(memory_limit.rstrip("mb"))
            return int(value)
        elif memory_limit.endswith("kb") or memory_limit.endswith("k"):
            value = float(memory_limit.rstrip("kb"))
            return int(value / 1024)
        else:
            # Assume bytes
            try:
                return int(float(memory_limit) / (1024 * 1024))
            except ValueError:
                raise ValueError(
                    f"Invalid memory limit format: {memory_limit}. "
                    f"Use format like '4g', '2048m', '512mb'"
                )
