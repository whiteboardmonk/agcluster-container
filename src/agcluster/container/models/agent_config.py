"""Agent configuration models - mirrors Claude SDK's ClaudeAgentOptions"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Literal, Union
from datetime import datetime


# MCP Server Configuration Types
class McpStdioServerConfig(BaseModel):
    """MCP server with stdio transport"""

    type: Optional[Literal["stdio"]] = "stdio"
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None


class McpSseServerConfig(BaseModel):
    """MCP server with SSE transport"""

    type: Literal["sse"]
    url: str
    headers: Optional[Dict[str, str]] = None


class McpHttpServerConfig(BaseModel):
    """MCP server with HTTP transport"""

    type: Literal["http"]
    url: str
    headers: Optional[Dict[str, str]] = None


# Union type for MCP server configs
McpServerConfig = Union[McpStdioServerConfig, McpSseServerConfig, McpHttpServerConfig]


# System Prompt Configuration
class SystemPromptPreset(BaseModel):
    """System prompt using Claude Code preset"""

    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: Optional[str] = None


# Sub-agent Definition
class AgentDefinition(BaseModel):
    """Sub-agent definition for multi-agent orchestration"""

    description: str = Field(..., description="When to use this agent")
    prompt: str = Field(..., description="Agent's system prompt")
    tools: Optional[List[str]] = Field(None, description="Allowed tools (inherits if omitted)")
    model: Optional[Literal["sonnet", "opus", "haiku", "inherit"]] = None


# Resource Limits
class ResourceLimits(BaseModel):
    """Container resource limits"""

    cpu_quota: Optional[int] = Field(None, description="CPU quota in microseconds")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g., '4g', '512m')")
    storage_limit: Optional[str] = Field(None, description="Storage limit (e.g., '10g')")


# Main Agent Configuration
class AgentConfig(BaseModel):
    """
    Agent configuration that mirrors Claude SDK's ClaudeAgentOptions.

    This configuration is passed to containers and used to initialize the Claude SDK.
    """

    # Metadata
    id: str = Field(..., description="Unique identifier for this config")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Description of agent's purpose")
    version: str = Field(default="1.0.0", description="Configuration version")

    # Core Claude SDK options
    allowed_tools: List[str] = Field(
        default_factory=list,
        description="List of allowed tool names (e.g., ['Bash', 'Read', 'Write'])",
    )
    system_prompt: Optional[Union[str, SystemPromptPreset]] = Field(
        None, description="System prompt as string or preset configuration"
    )
    mcp_servers: Dict[str, McpServerConfig] = Field(
        default_factory=dict, description="MCP server configurations keyed by server name"
    )
    permission_mode: Optional[Literal["default", "acceptEdits", "plan", "bypassPermissions"]] = (
        Field(None, description="Permission mode for tool execution")
    )

    # Multi-agent support
    agents: Optional[Dict[str, AgentDefinition]] = Field(
        None, description="Sub-agent definitions for multi-agent orchestration"
    )

    # Resource limits
    resource_limits: Optional[ResourceLimits] = None

    # Advanced options
    max_turns: Optional[int] = Field(None, description="Maximum conversation turns")
    model: Optional[str] = Field(None, description="Claude model to use")
    cwd: Optional[str] = Field(None, description="Working directory for agent")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    setting_sources: Optional[List[Literal["user", "project", "local"]]] = Field(
        None, description="Filesystem settings to load"
    )

    # Extra files in container
    extra_files: Optional[Dict[str, bytes]] = Field(
        None, description="Extra files to mount in the container (key: relative path, value: content in bytes)"
    )

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("allowed_tools")
    @classmethod
    def validate_tools(cls, v: List[str]) -> List[str]:
        """Validate tool names"""
        valid_tools = {
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Grep",
            "Glob",
            "Task",
            "WebFetch",
            "WebSearch",
            "TodoWrite",
            "NotebookEdit",
            "BashOutput",
            "KillBash",
            "ExitPlanMode",
            "ListMcpResources",
            "ReadMcpResource",
        }

        for tool in v:
            # Allow MCP tools (format: mcp__server__tool)
            if tool.startswith("mcp__"):
                continue

            if tool not in valid_tools:
                raise ValueError(f"Invalid tool: {tool}. Must be one of {valid_tools}")

        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate config ID format"""
        if not v:
            raise ValueError("Config ID cannot be empty")

        # Allow alphanumeric, hyphens, underscores
        import re

        if not re.match(r"^[a-z0-9\-_]+$", v):
            raise ValueError(
                "Config ID must contain only lowercase letters, numbers, hyphens, and underscores"
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "code-assistant",
                "name": "Code Assistant",
                "description": "Full-stack development agent",
                "allowed_tools": ["Bash", "Read", "Write", "Edit", "Grep"],
                "system_prompt": {
                    "type": "preset",
                    "preset": "claude_code",
                    "append": "Follow TDD principles.",
                },
                "permission_mode": "acceptEdits",
                "resource_limits": {"cpu_quota": 200000, "memory_limit": "4g"},
            }
        }


# Request/Response models for API
class AgentConfigCreateRequest(BaseModel):
    """Request to create a new agent configuration"""

    config: AgentConfig


class AgentConfigResponse(BaseModel):
    """Response containing agent configuration"""

    config: AgentConfig
    message: Optional[str] = None


class AgentConfigListResponse(BaseModel):
    """Response containing list of configurations"""

    configs: List[AgentConfig]
    total: int
