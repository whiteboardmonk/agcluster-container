"""Agent management endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List

from agcluster.container.models.schemas import AgentCreateRequest, AgentCreateResponse, AgentInfo

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
