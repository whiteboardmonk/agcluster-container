"""Translation layer between OpenAI format and Claude SDK messages"""

import time
import uuid
from typing import Dict, Any, AsyncIterator
import json


def generate_completion_id() -> str:
    """Generate OpenAI-style completion ID"""
    return f"chatcmpl-{uuid.uuid4().hex[:12]}"


def claude_message_to_openai_text(message: Dict[str, Any]) -> str:
    """
    Extract text content from Claude SDK message

    Args:
        message: Message from Claude SDK container

    Returns:
        Text content as string
    """
    if message.get("type") == "message":
        data = message.get("data", {})
        return data.get("content", "")

    elif message.get("type") == "error":
        return f"[Error: {message.get('message', 'Unknown error')}]"

    return ""


async def stream_to_openai_sse(
    container_stream: AsyncIterator[Dict[str, Any]],
    model: str
) -> AsyncIterator[str]:
    """
    Convert Claude SDK container stream to OpenAI SSE format

    Args:
        container_stream: Async iterator of messages from container
        model: Model name to include in response

    Yields:
        SSE-formatted strings
    """
    completion_id = generate_completion_id()
    created_timestamp = int(time.time())

    async for message in container_stream:
        message_type = message.get("type")

        if message_type == "message":
            # Extract data and classify message type
            data = message.get("data", {})
            msg_type = data.get("type")

            # Stream user-facing content
            if msg_type == "content":
                content = data.get("content", "")

                if content:
                    # Format as OpenAI delta chunk
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_timestamp,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": content
                            },
                            "finish_reason": None
                        }]
                    }

                    yield f"data: {json.dumps(chunk)}\n\n"

            # Stream tool execution events for UI panels
            # Use Vercel AI SDK's data stream protocol for custom data
            elif msg_type in ["tool_start", "tool_use", "tool_complete", "thinking"]:
                # Send as Vercel AI SDK data-tool part
                # Format: data: {"type":"data-tool","data":{...}}
                # The UI can process this through useChat's onToolCall or custom data handlers
                data_part = {
                    "type": "data-tool",
                    "data": data
                }
                yield f"data: {json.dumps(data_part)}\n\n"

            # Stream todo updates for task list panel
            elif msg_type == "todo_update":
                # Send as Vercel AI SDK data-todo part
                data_part = {
                    "type": "data-todo",
                    "data": data
                }
                yield f"data: {json.dumps(data_part)}\n\n"

            # Skip metadata and system messages in streaming
            # They're filtered out - only user-facing content is streamed

        elif message_type == "complete":
            # Send final chunk with finish_reason
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }

            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
            break

        elif message_type == "error":
            # Send error as content then finish
            error_msg = message.get("message", "Unknown error")

            error_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"\n\n[Error: {error_msg}]\n"
                    },
                    "finish_reason": "error"
                }]
            }

            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            break


def create_openai_completion_response(
    content: str,
    model: str,
    usage: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    Create OpenAI-compatible completion response (non-streaming)

    Args:
        content: Response content (cleaned, no internal objects)
        model: Model name
        usage: Token usage dict (input_tokens, output_tokens, total_tokens)

    Returns:
        OpenAI-compatible response dict
    """
    # Use real usage if provided, otherwise default to 0
    usage_data = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    if usage:
        usage_data = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }

    return {
        "id": generate_completion_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": usage_data
    }


async def stream_claude_events(
    container_stream: AsyncIterator[Dict[str, Any]]
) -> AsyncIterator[str]:
    """
    Stream Claude SDK events in their native format (for Edge route transformation)

    This streams events directly from the container with minimal formatting,
    allowing the Next.js Edge route to transform them into Vercel AI SDK format.

    Args:
        container_stream: Async iterator of messages from container

    Yields:
        SSE-formatted Claude events
    """
    async for message in container_stream:
        message_type = message.get("type")

        if message_type == "message":
            # Extract data from message
            data = message.get("data", {})
            msg_type = data.get("type")

            # Stream all message types with their data
            event_data = {
                "type": message_type,
                "msg_type": msg_type,
                "data": data
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        elif message_type == "complete":
            # Send completion event
            event_data = {
                "type": "complete",
                "status": message.get("status", "success")
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            yield "data: [DONE]\n\n"
            break

        elif message_type == "error":
            # Send error event
            event_data = {
                "type": "error",
                "message": message.get("message", "Unknown error")
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            yield "data: [DONE]\n\n"
            break
