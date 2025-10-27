"""Claude-native chat endpoint for AgCluster UI"""

import logging
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel, Field

from agcluster.container.models.schemas import ChatMessage
from agcluster.container.core.session_manager import session_manager, SessionNotFoundError
from agcluster.container.core.translator import stream_claude_events

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentChatRequest(BaseModel):
    """Request model for agent chat"""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[str] = Field(
        None, alias="sessionId", description="Session ID from /api/agents/launch"
    )


@router.post("/chat")
async def agent_chat(
    request: AgentChatRequest,
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Claude-native streaming chat endpoint for AgCluster UI

    Returns Claude SDK events directly (tool, thinking, todo, artifact) for
    transformation by the Next.js Edge route into Vercel AI SDK format.

    Args:
        request: Chat request with messages and optional session ID
        authorization: Bearer token (Anthropic API key)
        x_session_id: Optional session ID header

    Returns:
        Streaming response with Claude SDK events
    """

    # Extract API key from Authorization header
    api_key = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            api_key = parts[1]

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Provide: 'Bearer YOUR_ANTHROPIC_API_KEY'",
        )

    # Get session ID from request body or header
    session_id = request.session_id or x_session_id

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID required. Launch a session via /api/agents/launch first.",
        )

    # Extract the user's message (last message with role "user")
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found in request")

    try:
        # Get existing session
        logger.info(f"Using session: {session_id}")
        try:
            agent_container = await session_manager.get_session(session_id)
        except SessionNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found. Launch a new session via /api/agents/launch",
            )

        logger.info(
            f"Processing message for agent {agent_container.agent_id} " f"(session: {session_id})"
        )

        # Stream Claude SDK events
        return StreamingResponse(
            stream_claude_events(agent_container.query(user_message)),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agent chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
