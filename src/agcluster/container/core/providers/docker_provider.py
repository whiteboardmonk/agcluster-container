"""Docker provider implementation using HTTP/SSE communication"""

import asyncio
import docker
import httpx
import json
import logging
import uuid
import tarfile
import io
from typing import Dict, Any, AsyncIterator
from datetime import datetime, timezone
from fastapi import HTTPException

from .base import ContainerProvider, ContainerInfo, ProviderConfig

logger = logging.getLogger(__name__)


class DockerProvider(ContainerProvider):
    """
    Docker-based container provider.

    Uses local Docker daemon to create and manage containers.
    Communication with agent containers via HTTP/SSE on port 3000.
    """

    def __init__(self, network_name: str = "agcluster-container_agcluster-network"):
        """
        Initialize Docker provider.

        Args:
            network_name: Docker network name for containers
        """
        self._docker_client = None
        self.network_name = network_name
        self.active_containers: Dict[str, ContainerInfo] = {}

    @property
    def docker_client(self):
        """Lazy initialization of Docker client"""
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def create_container(self, session_id: str, config: ProviderConfig) -> ContainerInfo:
        """
        Create a new Docker container for the agent.

        Args:
            session_id: Unique session identifier
            config: Provider configuration

        Returns:
            ContainerInfo: Information about the created container

        Raises:
            ValueError: If Docker image not found
            RuntimeError: If container creation fails
        """
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        container_name = f"agcluster-{agent_id}"

        logger.info(f"Creating Docker container for session {session_id}, agent {agent_id}")

        try:
            # Prepare environment
            # Handle system_prompt which can be str or SystemPromptPreset (Pydantic model)
            system_prompt_value = config.system_prompt
            if hasattr(system_prompt_value, "model_dump"):
                # It's a Pydantic model (SystemPromptPreset), convert to dict
                system_prompt_value = system_prompt_value.model_dump()

            env = {
                "AGENT_ID": agent_id,
                "ANTHROPIC_API_KEY": config.api_key,
                "AGENT_CONFIG_JSON": json.dumps(
                    {
                        "id": config.platform,
                        "name": f"Agent {agent_id}",
                        "allowed_tools": config.allowed_tools,
                        "system_prompt": system_prompt_value,
                        "permission_mode": "acceptEdits",
                        "max_turns": config.max_turns,
                    }
                ),
            }

            # Create container
            container = self.docker_client.containers.run(
                image="agcluster/agent:latest",
                name=container_name,
                detach=True,
                # Environment
                environment=env,
                # Network
                network=self.network_name,
                # Resource limits from config
                mem_limit=config.memory_limit,
                cpu_quota=config.cpu_quota,
                # Security
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                # Volume for workspace
                volumes={f"agcluster-workspace-{agent_id}": {"bind": "/workspace", "mode": "rw"}},
                # Labels
                labels={
                    "agcluster": "true",
                    "agcluster.session_id": session_id,
                    "agcluster.agent_id": agent_id,
                    "agcluster.provider": "docker",
                },
            )

            # Wait for container to be ready
            await asyncio.sleep(3)  # Give container time to start HTTP server
            logger.info(f"Container {container_name} started, waiting for health check...")

            # Get container IP
            container.reload()
            networks = container.attrs["NetworkSettings"]["Networks"]
            if networks:
                container_ip = list(networks.values())[0]["IPAddress"]
            else:
                container_ip = container.attrs["NetworkSettings"]["IPAddress"]

            if not container_ip:
                raise RuntimeError("Failed to get container IP address")

            # Build endpoint URL (HTTP on port 3000)
            endpoint_url = f"http://{container_ip}:3000"

            # Wait for HTTP health check
            try:
                await self._wait_for_health(endpoint_url, timeout=10)
            except TimeoutError:
                logger.warning("Health check timed out, but container is running")

            # Upload extra files if provided
            if config.extra_files:
                logger.info(f"Uploading {len(config.extra_files)} extra files to container")
                try:
                    # Create tar archive in memory
                    tar_buffer = io.BytesIO()
                    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                        for file_path, content in config.extra_files.items():
                            logger.debug(
                                f"Adding file to tar: {file_path} (size: {len(content)} bytes)"
                            )

                            # Create tarinfo
                            tarinfo = tarfile.TarInfo(name=file_path)
                            tarinfo.size = len(content)
                            tarinfo.mode = 0o644  # rw-r--r--
                            tarinfo.mtime = int(datetime.now(timezone.utc).timestamp())
                            tarinfo.type = tarfile.REGTYPE  # Explicitly mark as regular file

                            # Add file to tar
                            tar.addfile(tarinfo, io.BytesIO(content))

                            logger.debug(
                                f"Added to tar: {file_path} - type={tarinfo.type}, "
                                f"isfile={tarinfo.isfile()}, isdir={tarinfo.isdir()}"
                            )

                    # Upload tar archive to container workspace
                    tar_buffer.seek(0)
                    tar_data = tar_buffer.getvalue()
                    container.put_archive("/workspace", tar_data)

                    logger.info(
                        f"Successfully uploaded {len(config.extra_files)} extra files to /workspace"
                    )
                except Exception as e:
                    logger.error(f"Error uploading extra files: {e}")
                    # Continue even if upload fails - don't fail container creation

            # Create container info with API key hash for session ownership validation
            import hashlib

            api_key_hash = hashlib.sha256(config.api_key.encode()).hexdigest()

            container_info = ContainerInfo(
                container_id=container.id,
                endpoint_url=endpoint_url,
                status="running",
                platform="docker",
                metadata={
                    "container_name": container_name,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "container_ip": container_ip,
                    "api_key_hash": api_key_hash,  # For session ownership validation
                },
            )

            self.active_containers[session_id] = container_info
            logger.info(f"Container {container_name} created successfully at {endpoint_url}")

            return container_info

        except docker.errors.ImageNotFound:
            logger.error("Docker image agcluster/agent:latest not found")
            raise ValueError("Agent image not found: agcluster/agent:latest")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error creating container: {e}")
            raise RuntimeError(f"Failed to create container: {str(e)}")

    async def stop_container(self, container_id: str) -> bool:
        """
        Stop and remove a Docker container.

        Args:
            container_id: Container ID to stop

        Returns:
            bool: True if successfully stopped
        """
        try:
            container = self.docker_client.containers.get(container_id)
            logger.info(f"Stopping container {container_id}")

            container.stop(timeout=10)
            container.remove()

            # Remove from active containers
            session_id = None
            for sid, info in list(self.active_containers.items()):
                if info.container_id == container_id:
                    session_id = sid
                    break

            if session_id:
                del self.active_containers[session_id]

            logger.info(f"Container {container_id} stopped and removed")
            return True

        except docker.errors.NotFound:
            logger.warning(f"Container {container_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {e}")
            return False

    async def get_container_status(self, container_id: str) -> str:
        """
        Get the current status of a Docker container.

        Args:
            container_id: Container ID

        Returns:
            str: Status (running, stopped, error)
        """
        try:
            container = self.docker_client.containers.get(container_id)
            container.reload()
            return container.status
        except docker.errors.NotFound:
            return "not_found"
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return "error"

    async def execute_query(
        self, container_info: ContainerInfo, query: str, conversation_history: list[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute query via HTTP/SSE.

        Args:
            container_info: Container information with endpoint URL
            query: User query
            conversation_history: Conversation history (currently unused)

        Yields:
            Dict[str, Any]: Streamed response messages
        """
        url = f"{container_info.endpoint_url}/query"

        logger.debug(f"Sending query to {url}")

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
            logger.error(f"HTTP error querying container: {e}")
            yield {"type": "error", "message": f"HTTP error: {e.response.status_code}"}
        except httpx.RequestError as e:
            logger.error(f"Request error querying container: {e}")
            yield {"type": "error", "message": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error querying container: {e}")
            yield {"type": "error", "message": f"Unexpected error: {str(e)}"}

    async def upload_files(
        self, container_id: str, files: list[Dict[str, Any]], target_path: str, overwrite: bool
    ) -> list[str]:
        """
        Upload files to a Docker container using tar archive.

        Args:
            container_id: Container ID
            files: List of file dictionaries
            target_path: Target directory path
            overwrite: Whether to overwrite existing files

        Returns:
            list[str]: List of successfully uploaded filenames

        Raises:
            HTTPException: If upload fails
        """
        try:
            container = self.docker_client.containers.get(container_id)
        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_id} not found")

        uploaded_files = []

        try:
            # Check for existing files if overwrite=False
            if not overwrite:
                for file_info in files:
                    file_path = f"{target_path}/{file_info['safe_name']}"
                    exec_result = container.exec_run(["test", "-f", file_path])
                    if exec_result.exit_code == 0:  # File exists
                        raise HTTPException(
                            status_code=409,
                            detail=f"File '{file_info['safe_name']}' already exists. "
                            "Set overwrite=true to replace it.",
                        )

            # Create tar archive in memory
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                for file_info in files:
                    # Create tarinfo
                    tarinfo = tarfile.TarInfo(name=file_info["safe_name"])
                    tarinfo.size = len(file_info["content"])
                    tarinfo.mode = 0o644  # rw-r--r--
                    tarinfo.mtime = int(datetime.now(timezone.utc).timestamp())

                    # Add file to tar
                    tar.addfile(tarinfo, io.BytesIO(file_info["content"]))
                    uploaded_files.append(file_info["safe_name"])

            # Upload tar archive to container
            tar_buffer.seek(0)
            tar_data = tar_buffer.getvalue()

            # Use put_archive to upload files
            container.put_archive(target_path, tar_data)

            logger.info(
                f"Uploaded {len(uploaded_files)} files to container {container_id}:{target_path}"
            )

            return uploaded_files

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading files to container {container_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

    async def list_containers(self) -> list[ContainerInfo]:
        """
        List all active Docker containers.

        Returns:
            list[ContainerInfo]: List of active containers
        """
        return list(self.active_containers.values())

    async def cleanup(self):
        """
        Cleanup Docker provider resources.

        Stops all active containers and closes Docker client.
        """
        logger.info(
            f"Cleaning up Docker provider ({len(self.active_containers)} active containers)"
        )

        # Stop all active containers
        for session_id, container_info in list(self.active_containers.items()):
            try:
                await self.stop_container(container_info.container_id)
            except Exception as e:
                logger.error(f"Error stopping container {container_info.container_id}: {e}")

        # Close Docker client
        if self._docker_client:
            self._docker_client.close()
            self._docker_client = None

        logger.info("Docker provider cleanup complete")

    async def _wait_for_health(self, endpoint_url: str, timeout: int = 30):
        """
        Wait for container HTTP health endpoint to respond.

        Args:
            endpoint_url: Base URL of container
            timeout: Timeout in seconds

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
                            logger.info(f"Container health check passed at {endpoint_url}")
                            return
                except (httpx.RequestError, httpx.HTTPStatusError):
                    # Server not ready yet
                    await asyncio.sleep(0.5)
                    continue

                await asyncio.sleep(0.5)

        raise TimeoutError(f"Container did not become healthy within {timeout}s")
