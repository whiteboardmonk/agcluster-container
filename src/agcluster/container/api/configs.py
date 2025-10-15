"""Configuration management endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List

from agcluster.container.core.config_loader import (
    load_config_from_id,
    list_available_configs,
    ConfigNotFoundError
)
from agcluster.container.models.schemas import ConfigInfo, ConfigListResponse

router = APIRouter()


@router.get("/", response_model=ConfigListResponse)
async def list_configs():
    """
    List all available agent configurations

    Returns list of both preset configs and user configs
    """
    try:
        configs = list_available_configs()

        # Convert to ConfigInfo format
        config_list = []
        for config in configs:
            config_list.append(ConfigInfo(
                id=config.id,
                name=config.name,
                description=config.description,
                version=config.version,
                allowed_tools=config.allowed_tools,
                has_mcp_servers=bool(config.mcp_servers),
                has_sub_agents=bool(config.agents),
                permission_mode=config.permission_mode
            ))

        return ConfigListResponse(
            configs=config_list,
            total=len(config_list)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list configs: {str(e)}")


@router.get("/{config_id}")
async def get_config(config_id: str):
    """
    Get detailed configuration by ID

    Args:
        config_id: Configuration ID (e.g., "code-assistant")

    Returns:
        Full agent configuration
    """
    try:
        config = load_config_from_id(config_id)

        # Return full config as dict
        return config.model_dump()

    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")
