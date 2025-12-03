"""Agent management endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List
import uuid

from agcluster.container.models.schemas import (
    AgentCreateRequest,
    AgentCreateResponse,
    AgentInfo,
    LaunchRequest,
    LaunchResponse,
    SessionInfo,
    SessionListResponse,
)
from agcluster.container.core.session_manager import session_manager, SessionNotFoundError

router = APIRouter()


@router.post("/", response_model=AgentCreateResponse)
async def create_agent(request: AgentCreateRequest):
    """Create a new agent"""
    # TODO: Implement agent creation
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/", response_model=List[AgentInfo])
async def list_agents():
    """List all agents"""
    # TODO: Implement agent listing
    return []


# New config-based endpoints (MUST come before /{agent_id} catch-all)


@router.post("/launch", response_model=LaunchResponse)
async def launch_agent(request: LaunchRequest):
    """
    Launch a new agent from configuration

    Args:
        request: LaunchRequest with either config_id or inline config

    Returns:
        LaunchResponse with session_id for subsequent chat requests

    Example with config_id:
        POST /api/agents/launch
        {
            "api_key": "sk-ant-...",
            "config_id": "code-assistant"
        }

    Example with inline config:
        POST /api/agents/launch
        {
            "api_key": "sk-ant-...",
            "config": {
                "id": "my-custom",
                "name": "My Custom Agent",
                "allowed_tools": ["Bash", "Read", "Write"]
            }
        }
    """
    try:
        # Validate request
        if not request.config_id and not request.config:
            raise HTTPException(
                status_code=400, detail="Either config_id or config must be provided"
            )

        # Generate conversation ID (used as session key)
        conversation_id = str(uuid.uuid4())

        # Create session from config with optional provider and MCP credentials
        session_id, agent_container = await session_manager.create_session_from_config(
            conversation_id=conversation_id,
            api_key=request.api_key,
            config_id=request.config_id,
            config=request.config,
            provider=request.provider,
            mcp_env=request.mcp_env,
        )

        return LaunchResponse(
            session_id=session_id,
            agent_id=agent_container.agent_id,
            config_id=agent_container.config_id,
            status="running",
            message=f"Agent launched successfully from config {agent_container.config_id}",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch agent: {str(e)}")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """
    List all active agent sessions

    Returns:
        SessionListResponse with list of active sessions and metadata
    """
    try:
        sessions_dict = session_manager.list_sessions()

        sessions_list = []
        for session_id, session_data in sessions_dict.items():
            sessions_list.append(
                SessionInfo(
                    session_id=session_data["session_id"],
                    agent_id=session_data["agent_id"],
                    config_id=session_data["config_id"],
                    status="running",  # Could be enhanced to check actual container status
                    created_at=session_data["created_at"],
                    last_active=session_data["last_active"],
                )
            )

        return SessionListResponse(sessions=sessions_list, total=len(sessions_list))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """
    Get information about a specific session

    Args:
        session_id: Session ID returned from /launch

    Returns:
        SessionInfo with session details
    """
    try:
        agent_container = await session_manager.get_session(session_id)

        return SessionInfo(
            session_id=session_id,
            agent_id=agent_container.agent_id,
            config_id=agent_container.config_id,
            status="running",
            created_at=agent_container.created_at,
            last_active=agent_container.last_active,
            config=None,  # Exclude config to avoid serialization issues
        )

    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def stop_session(session_id: str):
    """
    Stop and remove a session

    Args:
        session_id: Session ID to stop

    Returns:
        Success message
    """
    try:
        await session_manager.cleanup_session(session_id)

        return {"status": "success", "message": f"Session {session_id} stopped and removed"}

    except Exception:
        # Session might not exist, but that's okay
        return {"status": "success", "message": f"Session {session_id} stopped (or did not exist)"}


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    """
    Send interrupt signal to agent execution

    Args:
        session_id: Session ID to interrupt

    Returns:
        Success message
    """
    try:

        # Get session container
        agent_container = await session_manager.get_session(session_id)

        # Send interrupt message via HTTP (agent server now uses HTTP/SSE on port 3000)
        import httpx

        endpoint_url = agent_container.container_info.endpoint_url
        interrupt_url = f"{endpoint_url}/interrupt"

        async with httpx.AsyncClient() as client:
            response = await client.post(interrupt_url, timeout=5.0)
            response.raise_for_status()

        return {"status": "success", "message": f"Interrupt signal sent to session {session_id}"}

    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send interrupt: {str(e)}")


# Generic catch-all routes (MUST come AFTER specific routes)


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get agent information"""
    # TODO: Implement agent info retrieval
    raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Stop and remove an agent"""
    # TODO: Implement agent deletion
    raise HTTPException(status_code=501, detail="Not implemented yet")
