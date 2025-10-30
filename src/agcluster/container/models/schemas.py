"""Pydantic models for API requests and responses"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

# Import AgentConfig from agent_config module
from agcluster.container.models.agent_config import AgentConfig as FullAgentConfig


# OpenAI-compatible schemas


class ChatMessage(BaseModel):
    """Chat message in OpenAI format"""

    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = True
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)


class ChatCompletionChoice(BaseModel):
    """Choice in chat completion response"""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Dict[str, int]] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chunk in OpenAI format"""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


# AgCluster-specific schemas


class AgentConfig(BaseModel):
    """Agent configuration"""

    agent_id: str
    api_key: str = Field(..., description="Anthropic API key")
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    cpu_quota: Optional[int] = None
    memory_limit: Optional[str] = None


class AgentInfo(BaseModel):
    """Agent information"""

    agent_id: str
    container_id: Optional[str] = None
    status: Literal["creating", "running", "stopped", "error"]
    created_at: datetime
    last_active: Optional[datetime] = None


class AgentCreateRequest(BaseModel):
    """Request to create a new agent"""

    api_key: str = Field(..., description="Anthropic API key (BYOK)")
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    name: Optional[str] = None


class AgentCreateResponse(BaseModel):
    """Response after creating agent"""

    agent_id: str
    status: str
    message: str


# New schemas for config-based agent launch


class LaunchRequest(BaseModel):
    """Request to launch agent from configuration"""

    api_key: str = Field(..., description="Anthropic API key (BYOK)")
    config_id: Optional[str] = Field(None, description="ID of saved configuration to use")
    config: Optional[FullAgentConfig] = Field(None, description="Inline configuration")
    provider: Optional[str] = Field(
        None, description="Container provider (docker, fly_machines, cloudflare, vercel)"
    )
    mcp_env: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Runtime environment variables for MCP servers (e.g., {'github': {'GITHUB_PERSONAL_ACCESS_TOKEN': 'ghp_...'}})",
    )

    def validate_config_or_id(self):
        """Ensure either config_id or config is provided"""
        if not self.config_id and not self.config:
            raise ValueError("Either config_id or config must be provided")
        return self


class LaunchResponse(BaseModel):
    """Response after launching agent"""

    session_id: str = Field(..., description="Session ID for chat operations")
    agent_id: str = Field(..., description="Container agent ID")
    config_id: str = Field(..., description="Config ID used (inline-* for inline configs)")
    status: Literal["running", "error"] = "running"
    message: Optional[str] = None


class SessionInfo(BaseModel):
    """Information about an active session"""

    session_id: str
    agent_id: str
    config_id: str
    status: Literal["running", "idle", "error"]
    created_at: datetime
    last_active: datetime
    config: Optional[FullAgentConfig] = None


class SessionListResponse(BaseModel):
    """Response containing list of active sessions"""

    sessions: List[SessionInfo]
    total: int


class ConfigInfo(BaseModel):
    """Summary information about an agent configuration"""

    id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    allowed_tools: List[str]
    has_mcp_servers: bool = False
    has_sub_agents: bool = False
    permission_mode: Optional[str] = None


class ConfigListResponse(BaseModel):
    """Response containing list of available configurations"""

    configs: List[ConfigInfo]
    total: int
