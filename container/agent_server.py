"""FastAPI server with SSE running inside Docker container - wraps Claude Agent SDK"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
from datetime import datetime, timezone

from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Request model for query endpoint"""

    query: str
    history: list[Dict[str, Any]] = []


class AgentServer:
    """FastAPI server with SSE managing Claude SDK inside container"""

    def __init__(self):
        self.agent_id = os.environ.get("AGENT_ID", "unknown")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.config_path = os.environ.get("CONFIG_PATH", "/config/agent-config.json")
        self.config = None
        self.sdk_client = None  # Will be initialized in async context
        self.last_tool_name = None  # Track the last tool used for completion events

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load agent configuration from JSON env var, mounted file, or legacy env vars"""

        # Priority 1: AGENT_CONFIG_JSON environment variable (Docker Compose mode)
        config_json = os.environ.get("AGENT_CONFIG_JSON")
        if config_json:
            logger.info("Loading config from AGENT_CONFIG_JSON environment variable")
            try:
                self.config = json.loads(config_json)
                logger.info(f"Loaded config: {self.config.get('id')} - {self.config.get('name')}")
                logger.info(f"Tools: {self.config.get('allowed_tools')}")
                logger.info(f"Permission mode: {self.config.get('permission_mode', 'default')}")
                return
            except Exception as e:
                logger.error(f"Failed to parse AGENT_CONFIG_JSON: {e}")
                raise ValueError(f"Invalid config JSON: {e}")

        # Priority 2: Mounted config file
        config_file = Path(self.config_path)
        if config_file.exists():
            logger.info(f"Loading config from {self.config_path}")
            try:
                with open(config_file, "r") as f:
                    self.config = json.load(f)

                logger.info(f"Loaded config: {self.config.get('id')} - {self.config.get('name')}")
                logger.info(f"Tools: {self.config.get('allowed_tools')}")
                logger.info(f"Permission mode: {self.config.get('permission_mode', 'default')}")
                return

            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                raise ValueError(f"Invalid config file: {e}")

        # Priority 3: Legacy environment variables (backward compatible)
        logger.info("No config found, using legacy environment variables")
        self.config = {
            "id": "legacy",
            "name": "Legacy Agent",
            "allowed_tools": os.environ.get(
                "ALLOWED_TOOLS", "Bash,Read,Write,ListMcpResources,ReadMcpResource"
            ).split(","),
            "system_prompt": os.environ.get("SYSTEM_PROMPT", "You are a helpful AI assistant."),
            "permission_mode": "acceptEdits",
        }

    async def initialize_sdk(self):
        """Initialize Claude SDK client (call once at startup)"""
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

            # Build options from config
            options_dict = {
                "cwd": "/workspace",
                "allowed_tools": self.config.get("allowed_tools", ["Bash", "Read", "Write"]),
                "permission_mode": self.config.get("permission_mode", "acceptEdits"),
            }

            # Handle system prompt (string or preset object)
            system_prompt = self.config.get("system_prompt")
            if isinstance(system_prompt, dict):
                # System prompt preset with optional append - convert to string
                if system_prompt.get("type") == "preset":
                    # For preset types, use the append text as the system prompt
                    # The preset itself is handled by Claude SDK internally
                    options_dict["system_prompt"] = system_prompt.get("append", "")
            elif isinstance(system_prompt, str):
                # Direct string prompt
                options_dict["system_prompt"] = system_prompt

            # Add MCP servers if configured
            mcp_servers = self.config.get("mcp_servers", {})
            if mcp_servers:
                options_dict["mcp_servers"] = mcp_servers
                logger.info(f"Configured {len(mcp_servers)} MCP servers")

            # Add sub-agents if configured (multi-agent orchestration)
            agents = self.config.get("agents", {})
            if agents:
                options_dict["agents"] = agents
                logger.info(f"Configured {len(agents)} sub-agents: {list(agents.keys())}")

            # Add hook support if configured
            hooks = self.config.get("hooks", {})
            if hooks:
                try:
                    # Import HookMatcher if available
                    from claude_agent_sdk import HookMatcher

                    # Convert hooks configuration to SDK format
                    hook_config = {}

                    # Example: Add PreToolUse hooks for safety
                    if "PreToolUse" in hooks:
                        hook_config["PreToolUse"] = []
                        for hook in hooks["PreToolUse"]:
                            if isinstance(hook, dict):
                                matcher = hook.get("matcher", "*")
                                # For now, log hook events - real implementation would add callbacks
                                logger.info(f"Registered PreToolUse hook for: {matcher}")

                    if hook_config:
                        options_dict["hooks"] = hook_config
                        logger.info(f"Configured hooks: {list(hook_config.keys())}")
                except ImportError:
                    logger.debug("HookMatcher not available in current SDK version")

            # Configure Claude SDK options
            options = ClaudeAgentOptions(**options_dict)

            # Create client (maintains session across queries)
            self.sdk_client = ClaudeSDKClient(options)
            await self.sdk_client.__aenter__()

            logger.info(f"Claude SDK client initialized for agent {self.agent_id}")
            logger.info(
                f"Config: {self.config.get('id')} with tools: {options_dict['allowed_tools']}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Claude SDK: {e}", exc_info=True)
            raise

    async def process_query_stream(self, query: str, request: Request) -> AsyncIterator[str]:
        """
        Process query with Claude SDK and stream responses via SSE.

        Yields SSE-formatted messages:
        - data: {JSON}\n\n

        Supports cancellation via request.is_disconnected()
        """
        try:
            if not self.sdk_client:
                raise RuntimeError("Claude SDK client not initialized")

            # Check if this is a slash command
            is_slash_command = query.strip().startswith("/")
            if is_slash_command:
                logger.info(f"Processing slash command: {query[:100]}...")
            else:
                logger.info(f"Processing query: {query[:100]}...")

            # Send query to Claude SDK client (maintains session)
            await self.sdk_client.query(query)

            # Stream responses from the session
            message_count = 0
            async for message in self.sdk_client.receive_messages():
                # Check for client disconnection (cancellation support)
                if await request.is_disconnected():
                    logger.info("Client disconnected, stopping query processing")
                    if self.sdk_client:
                        try:
                            await self.sdk_client.interrupt()
                        except Exception as e:
                            logger.error(f"Error interrupting SDK: {e}")
                    break

                message_count += 1

                # Format and yield message (may return list for multiple events)
                formatted = await self._format_message(message)
                if formatted:
                    # Handle both single events and lists of events
                    events_to_send = formatted if isinstance(formatted, list) else [formatted]
                    for event in events_to_send:
                        yield f"data: {json.dumps({'type': 'message', 'data': event, 'sequence': message_count})}\n\n"

                # Check for completion (ResultMessage indicates completion)
                if type(message).__name__ == "ResultMessage":
                    yield f"data: {json.dumps({'type': 'complete', 'status': 'success', 'total_messages': message_count})}\n\n"
                    break

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            error_data = {"type": "error", "message": str(e), "error_type": type(e).__name__}
            yield f"data: {json.dumps(error_data)}\n\n"

    async def _format_message(self, message) -> Optional[Dict[str, Any]]:
        """
        Classify Claude SDK messages for OpenAI-compatible formatting

        Returns dict with 'type' field:
        - type: "content" → User-facing assistant response
        - type: "tool_use" → Tool execution info
        - type: "tool_start" → Tool execution started
        - type: "tool_complete" → Tool execution completed
        - type: "thinking" → Agent thinking process
        - type: "todo_update" → TodoWrite tool update
        - type: "metadata" → Usage stats, cost info (from ResultMessage)
        - type: "system" → Debug/session info
        - None → Skip this message
        """
        try:
            # Log every message type we receive
            logger.info(f"📨 Received message type: {type(message).__name__}")
            # Import types for checking - updated to match documentation
            from claude_agent_sdk import AssistantMessage, ToolUseBlock, ToolResultBlock, TextBlock

            # Try to import additional message types that may not be available
            try:
                from claude_agent_sdk import (
                    SystemMessage,
                    ResultMessage,
                    UserMessage,
                    ThinkingBlock,
                )
            except ImportError:
                SystemMessage = None
                ResultMessage = None
                UserMessage = None
                ThinkingBlock = None

            # Check if ThinkingBlock is available (may not be in current SDK)
            if ThinkingBlock is None:
                logger.debug("ThinkingBlock not available in current SDK version")

            # ===== USER-FACING CONTENT =====
            if isinstance(message, AssistantMessage):
                # Log blocks in this message
                block_types = [type(block).__name__ for block in message.content]
                logger.info(f"  AssistantMessage contains blocks: {block_types}")

                # Extract text content and tool use
                for block in message.content:
                    if ThinkingBlock and isinstance(block, ThinkingBlock):
                        # Return thinking block as event
                        return {
                            "type": "thinking",
                            "content": block.text,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    elif isinstance(block, TextBlock):
                        # If we had a tool running, mark it as complete before showing text
                        if self.last_tool_name:
                            # Return tool complete event first
                            # (Note: This is a simplification - in full impl we'd need a queue)
                            self.last_tool_name = None

                        return {"type": "content", "role": "assistant", "content": block.text}
                    elif isinstance(block, ToolUseBlock):
                        # Get tool_use_id from the block
                        tool_use_id = getattr(
                            block, "id", f"tool_{block.name}_{datetime.now().timestamp()}"
                        )

                        # Track this tool for completion event
                        self.last_tool_name = block.name

                        # Emit tool start event with tool_use_id for matching
                        tool_start_event = {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_use_id": tool_use_id,
                            "tool_input": block.input,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "started",
                            "content": f"Using tool: {block.name}",
                        }

                        # Check if this is TodoWrite tool - emit both tool_start AND todo_update
                        if block.name == "TodoWrite" and isinstance(block.input, dict):
                            todos = block.input.get("todos", [])
                            if todos:
                                # Return BOTH tool_start and todo_update as a list
                                todo_update_event = {
                                    "type": "todo_update",
                                    "todos": todos,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                                return [tool_start_event, todo_update_event]

                        # For other tools, just return tool_start
                        return tool_start_event
                    elif isinstance(block, ToolResultBlock):
                        # Emit tool complete event when tool finishes
                        logger.info(f"ToolResultBlock received: {block}")
                        return {
                            "type": "tool_complete",
                            "tool_name": getattr(block, "tool_use_id", "unknown"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "completed",
                            "output": getattr(block, "content", None),
                            "is_error": getattr(block, "is_error", False),
                        }

            # ===== METADATA (extract but don't include in user-facing content) =====
            if ResultMessage and isinstance(message, ResultMessage):
                return {
                    "type": "metadata",
                    "final_content": getattr(message, "result", ""),
                    "cost_usd": getattr(message, "total_cost_usd", 0),
                    "duration_ms": getattr(message, "duration_ms", 0),
                    "usage": {
                        "input_tokens": getattr(message, "usage", {}).get("input_tokens", 0),
                        "output_tokens": getattr(message, "usage", {}).get("output_tokens", 0),
                        "total_tokens": (
                            getattr(message, "usage", {}).get("input_tokens", 0)
                            + getattr(message, "usage", {}).get("output_tokens", 0)
                        ),
                    },
                }

            # ===== SYSTEM/DEBUG (skip in production responses) =====
            if SystemMessage and isinstance(message, SystemMessage):
                return {
                    "type": "system",
                    "subtype": getattr(message, "subtype", ""),
                    "session_id": getattr(message, "data", {}).get("session_id", ""),
                }

            # ===== USER MESSAGES (may contain ToolResultBlock) =====
            if UserMessage and isinstance(message, UserMessage):
                # Check if this UserMessage contains ToolResultBlock
                if hasattr(message, "content") and isinstance(message.content, list):
                    block_types = [type(block).__name__ for block in message.content]
                    logger.info(f"  UserMessage contains blocks: {block_types}")

                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            # Emit tool complete event
                            logger.info(f"✅ ToolResultBlock found in UserMessage: {block}")
                            return {
                                "type": "tool_complete",
                                "tool_name": getattr(block, "tool_use_id", "unknown"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "status": "completed",
                                "output": getattr(block, "content", None),
                                "is_error": getattr(block, "is_error", False),
                            }
                # Don't echo regular user text messages back
                return None

            # Unknown message type - skip
            logger.info(f"  ⚠️  Unknown message type, skipping: {type(message).__name__}")
            return None

        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return None


# Create FastAPI app
app = FastAPI(title="AgCluster Agent Server", version="2.0.0")

# Global server instance
server: Optional[AgentServer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize agent server and Claude SDK on startup"""
    global server
    agent_id = os.environ.get("AGENT_ID", "unknown")
    logger.info(f"Starting agent server for {agent_id}")
    logger.info("Initializing FastAPI with SSE on port 3000")

    server = AgentServer()
    await server.initialize_sdk()

    logger.info("Agent server ready")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_id": os.environ.get("AGENT_ID", "unknown"),
        "sdk_initialized": server.sdk_client is not None if server else False,
    }


@app.post("/query")
async def query_agent(query_request: QueryRequest, request: Request):
    """
    Process query and stream responses via SSE.

    Request:
    {
        "query": "user query text",
        "history": []  // Optional conversation history
    }

    Response: Server-Sent Events stream
    - data: {"type": "message", "data": {...}}\n\n
    - data: {"type": "complete", "status": "success"}\n\n
    """
    if not server:
        return {"error": "Agent server not initialized"}

    async def event_generator():
        async for event in server.process_query_stream(query_request.query, request):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/interrupt")
async def interrupt_execution():
    """Interrupt current query execution"""
    if not server or not server.sdk_client:
        return {"error": "Agent server not initialized"}

    try:
        await server.sdk_client.interrupt()
        logger.info("Successfully interrupted execution")
        return {"status": "interrupted"}
    except Exception as e:
        logger.error(f"Error during interrupt: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/upload")
async def upload_files_to_workspace(
    files: list[UploadFile] = File(...),
    target_path: str = Form("/workspace"),
    overwrite: bool = Form(False),
):
    """
    Upload files to workspace directory.

    Used by Fly.io provider to upload files via HTTP proxy.
    Docker provider uses tar archive method instead.

    Args:
        files: List of files to upload
        target_path: Target directory path (default: /workspace)
        overwrite: Whether to overwrite existing files

    Returns:
        Dict with uploaded filenames

    Security:
        - Path validation to prevent directory traversal
        - Filename sanitization
        - File existence checks
    """
    import re

    # Validate target path (must be within /workspace)
    workspace = Path("/workspace")
    target = Path(target_path)

    # Resolve and verify path is within workspace
    try:
        resolved_target = target.resolve()
        resolved_target.relative_to(workspace)
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=400, detail="Invalid target path: must be within /workspace"
        )

    # Ensure target directory exists
    resolved_target.mkdir(parents=True, exist_ok=True)

    uploaded_files = []

    for file in files:
        # Sanitize filename
        filename = os.path.basename(file.filename or "unnamed")
        filename = re.sub(r"[^\w\s\-\.]", "_", filename)

        if filename.startswith(".") or filename.startswith("-"):
            filename = "_" + filename[1:]

        if not filename or filename in [".", ".."]:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Full file path
        file_path = resolved_target / filename

        # Check if file exists (if overwrite=False)
        if not overwrite and file_path.exists():
            raise HTTPException(
                status_code=409,
                detail=f"File '{filename}' already exists. Set overwrite=true to replace it.",
            )

        # Write file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Set proper permissions (rw-r--r--)
            file_path.chmod(0o644)

            uploaded_files.append(filename)
            logger.info(f"Uploaded file: {file_path}")
        except Exception as e:
            logger.error(f"Error writing file {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

    return {
        "uploaded": uploaded_files,
        "total_files": len(uploaded_files),
        "target_path": str(resolved_target),
    }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,  # Changed from 8765 (WebSocket) to 3000 (HTTP)
        log_level="info",
    )
