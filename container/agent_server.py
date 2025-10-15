"""WebSocket server running inside Docker container - wraps Claude Agent SDK"""

import asyncio
import websockets
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class AgentServer:
    """WebSocket server managing Claude SDK inside container"""

    def __init__(self):
        self.agent_id = os.environ.get("AGENT_ID", "unknown")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.config_path = os.environ.get("CONFIG_PATH", "/config/agent-config.json")
        self.config = None
        self.sdk_client = None  # Will be initialized in async context

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load agent configuration from mounted file or environment variables"""
        config_file = Path(self.config_path)

        if config_file.exists():
            # Load from mounted config file (Phase 1+ approach)
            logger.info(f"Loading config from {self.config_path}")
            try:
                with open(config_file, 'r') as f:
                    self.config = json.load(f)

                logger.info(f"Loaded config: {self.config.get('id')} - {self.config.get('name')}")
                logger.info(f"Tools: {self.config.get('allowed_tools')}")
                logger.info(f"Permission mode: {self.config.get('permission_mode', 'default')}")

            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                raise ValueError(f"Invalid config file: {e}")
        else:
            # Fallback to environment variables (legacy/backward compatible)
            logger.info("No config file found, using environment variables (legacy mode)")
            self.config = {
                "id": "legacy",
                "name": "Legacy Agent",
                "allowed_tools": os.environ.get("ALLOWED_TOOLS", "Bash,Read,Write").split(","),
                "system_prompt": os.environ.get("SYSTEM_PROMPT", "You are a helpful AI assistant."),
                "permission_mode": "acceptEdits"
            }

    async def initialize_sdk(self):
        """Initialize Claude SDK client (call once at startup)"""
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

            # Build options from config
            options_dict = {
                "cwd": "/workspace",
                "allowed_tools": self.config.get("allowed_tools", ["Bash", "Read", "Write"]),
                "permission_mode": self.config.get("permission_mode", "acceptEdits")
            }

            # Handle system prompt (string or preset object)
            system_prompt = self.config.get("system_prompt")
            if isinstance(system_prompt, dict):
                # System prompt preset with optional append
                if system_prompt.get("type") == "preset":
                    options_dict["system_prompt_preset"] = system_prompt.get("preset")
                    if system_prompt.get("append"):
                        options_dict["system_prompt_append"] = system_prompt.get("append")
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

            # Configure Claude SDK options
            options = ClaudeAgentOptions(**options_dict)

            # Create client (maintains session across queries)
            self.sdk_client = ClaudeSDKClient(options)
            await self.sdk_client.__aenter__()

            logger.info(f"Claude SDK client initialized for agent {self.agent_id}")
            logger.info(f"Config: {self.config.get('id')} with tools: {options_dict['allowed_tools']}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude SDK: {e}", exc_info=True)
            raise

    async def handle_connection(self, websocket):
        """Handle WebSocket connection from host"""
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected to agent {self.agent_id}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get("type") == "query":
                        await self.process_query(websocket, data.get("content", ""))

                    elif data.get("type") == "interrupt":
                        await self.handle_interrupt(client_id)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling connection: {e}", exc_info=True)

    async def process_query(self, websocket, query: str):
        """Process query with Claude SDK and stream responses"""
        try:
            if not self.sdk_client:
                raise RuntimeError("Claude SDK client not initialized")

            logger.info(f"Processing query: {query[:100]}...")

            # Send query to Claude SDK client (maintains session)
            await self.sdk_client.query(query)

            # Stream responses from the session
            message_count = 0
            async for message in self.sdk_client.receive_messages():
                message_count += 1

                # Format and send message
                formatted = self._format_message(message)
                if formatted:
                    await websocket.send(json.dumps({
                        "type": "message",
                        "data": formatted,
                        "sequence": message_count
                    }))

                # Check for completion (ResultMessage indicates completion)
                if type(message).__name__ == 'ResultMessage':
                    await websocket.send(json.dumps({
                        "type": "complete",
                        "status": "success",
                        "total_messages": message_count
                    }))
                    break

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e),
                "error_type": type(e).__name__
            }))

    async def handle_interrupt(self, client_id: int):
        """Handle interrupt request"""
        logger.info(f"Interrupt requested for client {client_id}")
        # TODO: Implement Claude SDK interrupt when available

    def _format_message(self, message) -> Optional[Dict[str, Any]]:
        """
        Classify Claude SDK messages for OpenAI-compatible formatting

        Returns dict with 'type' field:
        - type: "content" → User-facing assistant response
        - type: "tool_use" → Tool execution info
        - type: "metadata" → Usage stats, cost info (from ResultMessage)
        - type: "system" → Debug/session info
        - None → Skip this message
        """
        try:
            # Import types for checking
            from claude_agent_sdk.types import AssistantMessage, ToolUseBlock, TextBlock

            # Try to import additional message types (may not all be available)
            try:
                from claude_agent_sdk.types import SystemMessage, ResultMessage, UserMessage
            except ImportError:
                SystemMessage = None
                ResultMessage = None
                UserMessage = None

            # ===== USER-FACING CONTENT =====
            if isinstance(message, AssistantMessage):
                # Extract text content
                for block in message.content:
                    if isinstance(block, TextBlock):
                        return {
                            "type": "content",
                            "role": "assistant",
                            "content": block.text
                        }
                    elif isinstance(block, ToolUseBlock):
                        return {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_input": block.input,
                            "content": f"Using tool: {block.name}"
                        }

            # ===== METADATA (extract but don't include in user-facing content) =====
            if ResultMessage and isinstance(message, ResultMessage):
                return {
                    "type": "metadata",
                    "final_content": getattr(message, 'result', ''),
                    "cost_usd": getattr(message, 'total_cost_usd', 0),
                    "duration_ms": getattr(message, 'duration_ms', 0),
                    "usage": {
                        "input_tokens": getattr(message, 'usage', {}).get("input_tokens", 0),
                        "output_tokens": getattr(message, 'usage', {}).get("output_tokens", 0),
                        "total_tokens": (
                            getattr(message, 'usage', {}).get("input_tokens", 0) +
                            getattr(message, 'usage', {}).get("output_tokens", 0)
                        )
                    }
                }

            # ===== SYSTEM/DEBUG (skip in production responses) =====
            if SystemMessage and isinstance(message, SystemMessage):
                return {
                    "type": "system",
                    "subtype": getattr(message, 'subtype', ''),
                    "session_id": getattr(message, 'data', {}).get("session_id", "")
                }

            # ===== SKIP USER ECHO =====
            if UserMessage and isinstance(message, UserMessage):
                return None  # Don't echo user messages back

            # Unknown message type - skip
            return None

        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return None


async def main():
    """Start WebSocket server"""
    agent_id = os.environ.get("AGENT_ID", "unknown")
    logger.info(f"Starting agent server for {agent_id}")
    logger.info("Listening on 0.0.0.0:8765")

    server = AgentServer()

    # Initialize Claude SDK client (maintains session across queries)
    await server.initialize_sdk()

    async with websockets.serve(
        server.handle_connection,
        "0.0.0.0",
        8765,
        ping_interval=20,
        ping_timeout=10
    ):
        logger.info("Agent server ready")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
