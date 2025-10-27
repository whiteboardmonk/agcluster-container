"""
Tool execution streaming endpoints via Server-Sent Events (SSE)
Bridges HTTP/SSE events from agent containers to SSE streams for frontend
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any
import httpx
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from agcluster.container.core.session_manager import session_manager, SessionNotFoundError
from agcluster.container.core.container_manager import container_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/tools/{session_id}/stream")
async def stream_tool_executions(session_id: str):
    """
    Stream tool execution events via SSE from agent container

    Event types sent to frontend:
    - tool_start: Tool execution began
    - tool_use: Tool is executing
    - tool_complete: Tool finished successfully
    - tool_error: Tool execution failed
    - todo_update: TodoWrite tool updated task list
    - thinking: Agent reasoning process

    Args:
        session_id: Agent session ID

    Returns:
        EventSourceResponse with SSE stream
    """
    # Get container for this session
    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Use container IP from AgentContainer object - agent server runs on port 3000
    agent_url = f"http://{container.container_ip}:3000"
    logger.info(f"Streaming tool events from {agent_url} for session {session_id}")

    async def event_generator() -> AsyncIterator[Dict[str, Any]]:
        """Generate SSE events by monitoring agent query endpoint"""
        # Note: This endpoint streams events from an ongoing agent query
        # The actual query is initiated from /chat/completions endpoint
        # This endpoint just passively monitors tool-related events

        retry_count = 0
        max_retries = 3
        keepalive_interval = 30  # Send keepalive every 30 seconds

        while retry_count < max_retries:
            try:
                # Create HTTP client with timeouts
                async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                    # Check agent health first
                    try:
                        health_response = await client.get(f"{agent_url}/health", timeout=5.0)
                        health_response.raise_for_status()
                        logger.info(f"Agent container healthy for session {session_id}")
                    except Exception as e:
                        raise ConnectionError(f"Agent container not responding: {e}")

                    retry_count = 0  # Reset on successful connection

                    # Send periodic keepalive pings while waiting for tool events
                    # In a real implementation, we'd subscribe to an SSE stream from the agent
                    # For now, we'll send keepalive pings
                    start_time = asyncio.get_event_loop().time()

                    while True:
                        # Send keepalive ping
                        current_time = asyncio.get_event_loop().time()
                        yield {
                            "event": "ping",
                            "data": json.dumps({
                                "timestamp": current_time,
                                "uptime": current_time - start_time
                            })
                        }

                        # Wait before next ping
                        await asyncio.sleep(keepalive_interval)

            except ConnectionError as e:
                retry_count += 1
                logger.error(f"Connection error in tool stream (attempt {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    # Send error event but keep stream alive for retry
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "message": f"Connection error, retrying... ({retry_count}/{max_retries})",
                            "error": str(e)
                        })
                    }
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    # Max retries reached
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "message": "Failed to connect to agent container after multiple attempts",
                            "error": str(e),
                            "fatal": True
                        })
                    }
                    break

            except Exception as e:
                logger.error(f"Unexpected error in tool stream: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "message": "Unexpected error",
                        "error": str(e),
                        "fatal": True
                    })
                }
                break

    return EventSourceResponse(event_generator())


@router.get("/api/resources/{session_id}")
async def get_resource_usage(session_id: str):
    """
    Get real-time resource usage for agent container

    Returns:
        CPU, memory, and disk usage statistics
    """
    # Get container for this session
    try:
        container = await session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Get Docker container stats
        docker_container = container_manager.provider.docker_client.containers.get(container.container_id)
        stats = docker_container.stats(stream=False)

        # Parse CPU usage
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        cpu_count = stats['cpu_stats']['online_cpus']

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

        # Parse memory usage
        memory_usage = stats['memory_stats'].get('usage', 0)
        memory_limit = stats['memory_stats'].get('limit', 1)
        memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

        # Get disk usage (from container filesystem)
        try:
            exec_result = docker_container.exec_run("df -h /workspace | tail -1 | awk '{print $5}'")
            disk_usage_str = exec_result.output.decode().strip().rstrip('%')
            disk_percent = float(disk_usage_str) if disk_usage_str else 0.0
        except Exception:
            disk_percent = 0.0

        return {
            "session_id": session_id,
            "container_id": container.container_id,
            "cpu": {
                "percent": round(cpu_percent, 2),
                "count": cpu_count
            },
            "memory": {
                "used_bytes": memory_usage,
                "limit_bytes": memory_limit,
                "percent": round(memory_percent, 2),
                "used_mb": round(memory_usage / (1024 * 1024), 2),
                "limit_mb": round(memory_limit / (1024 * 1024), 2)
            },
            "disk": {
                "percent": round(disk_percent, 2)
            },
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Error getting resource usage for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get resource usage: {str(e)}")
