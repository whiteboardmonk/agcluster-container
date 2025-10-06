"""Pydantic models for API requests and responses"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


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
