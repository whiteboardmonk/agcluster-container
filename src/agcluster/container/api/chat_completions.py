"""OpenAI-compatible chat completions endpoint"""

import logging
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional

from agcluster.container.models.schemas import ChatCompletionRequest, ChatCompletionResponse
from agcluster.container.core.session_manager import session_manager
from agcluster.container.core.translator import stream_to_openai_sse, create_openai_completion_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None),
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    OpenAI-compatible chat completions endpoint with session-based conversation management

    This endpoint accepts requests from LibreChat and other OpenAI-compatible clients.
    It maintains persistent Claude SDK sessions per conversation for context continuity.

    Two modes of operation:
    1. Session-based (new): Provide X-Session-ID from /api/agents/launch
    2. Conversation-based (legacy): Provide X-Conversation-ID from LibreChat

    Args:
        request: Chat completion request
        authorization: Bearer token (Anthropic API key)
        x_conversation_id: Optional conversation ID from LibreChat (legacy mode)
        x_session_id: Optional session ID from /api/agents/launch (new mode)

    Returns:
        Streaming or non-streaming response in OpenAI format
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
            detail="Missing or invalid Authorization header. Provide: 'Bearer YOUR_ANTHROPIC_API_KEY'"
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
        # Two modes: session-based (new) or conversation-based (legacy)
        if x_session_id:
            # New mode: Use existing session from /api/agents/launch
            logger.info(f"Using existing session: {x_session_id}")
            from agcluster.container.core.session_manager import SessionNotFoundError
            try:
                agent_container = await session_manager.get_session(x_session_id)
            except SessionNotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {x_session_id} not found. Launch a new session via /api/agents/launch"
                )
        else:
            # Legacy mode: Get or create session based on conversation ID
            logger.info(f"Using conversation-based session (legacy mode)")
            agent_container = await session_manager.get_or_create_session(
                conversation_id=x_conversation_id,
                api_key=api_key,
                system_prompt=None,  # Use default from config
                allowed_tools=None   # Use default from config
            )

        logger.info(
            f"Processing message for agent {agent_container.agent_id} "
            f"(session: {x_session_id or x_conversation_id or 'default'})"
        )

        # Query the container (session persists across queries)
        if request.stream:
            # Streaming response
            logger.info(f"Streaming response for agent {agent_container.agent_id}")

            return StreamingResponse(
                stream_to_openai_sse(
                    agent_container.query(user_message),
                    model=request.model
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        else:
            # Non-streaming response
            logger.info(f"Non-streaming response for agent {agent_container.agent_id}")

            # Collect all messages with type classification
            content_parts = []
            final_result = None
            usage_info = None

            async for message in agent_container.query(user_message):
                if message.get("type") == "message":
                    data = message.get("data", {})
                    msg_type = data.get("type")

                    if msg_type == "content":
                        # User-facing assistant text (streaming chunks)
                        content = data.get("content", "")
                        if content:
                            content_parts.append(content)

                    elif msg_type == "metadata":
                        # Extract final result and usage from ResultMessage
                        # ResultMessage.result contains the complete final response
                        final_result = data.get("final_content", "")
                        usage_info = data.get("usage")

                    elif msg_type == "tool_use":
                        # Future: Build tool_calls array
                        # For now: skip in non-streaming (user sees final result)
                        pass

                    # Ignore "system" type messages (debug info)

                elif message.get("type") == "error":
                    raise HTTPException(
                        status_code=500,
                        detail=message.get("message", "Unknown error")
                    )

            # Use final result if available, otherwise combine content parts
            # ResultMessage.result is the authoritative final response
            final_content = final_result if final_result else "".join(content_parts)

            response = create_openai_completion_response(
                content=final_content,
                model=request.model,
                usage=usage_info
            )

            return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
