"""Configuration management endpoints"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import yaml
import logging

from agcluster.container.core.config_loader import (
    load_config_from_id,
    list_available_configs,
    ConfigNotFoundError,
)
from agcluster.container.models.schemas import ConfigInfo, ConfigListResponse
from agcluster.container.models.agent_config import AgentConfig

router = APIRouter()
logger = logging.getLogger(__name__)


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
            config_list.append(
                ConfigInfo(
                    id=config.id,
                    name=config.name,
                    description=config.description,
                    version=config.version,
                    allowed_tools=config.allowed_tools,
                    has_mcp_servers=bool(config.mcp_servers),
                    has_sub_agents=bool(config.agents),
                    permission_mode=config.permission_mode,
                )
            )

        return ConfigListResponse(configs=config_list, total=len(config_list))

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


@router.post("/custom")
async def save_custom_config(config: AgentConfig):
    """
    Save a custom user-created agent configuration

    Saves configuration to ~/.agcluster/configs/custom/<config_id>.yaml

    Args:
        config: AgentConfig object with all required fields

    Returns:
        Success status and config_id
    """
    try:
        # Validate config has required fields
        if not config.id:
            raise HTTPException(status_code=400, detail="Config ID is required")

        # Create custom configs directory
        config_dir = Path.home() / ".agcluster" / "configs" / "custom"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Save config as YAML
        config_file = config_dir / f"{config.id}.yaml"

        with open(config_file, "w") as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved custom config: {config.id} to {config_file}")

        return {"status": "success", "config_id": config.id, "path": str(config_file)}

    except Exception as e:
        logger.error(f"Failed to save custom config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@router.get("/custom/list")
async def list_custom_configs():
    """
    List all custom user-created configurations

    Returns:
        List of custom configurations from ~/.agcluster/configs/custom/
    """
    try:
        config_dir = Path.home() / ".agcluster" / "configs" / "custom"

        if not config_dir.exists():
            return ConfigListResponse(configs=[], total=0)

        custom_configs = []

        for config_file in config_dir.glob("*.yaml"):
            try:
                with open(config_file, "r") as f:
                    config_data = yaml.safe_load(f)

                # Create AgentConfig from loaded data
                config = AgentConfig(**config_data)

                # Convert to ConfigInfo format
                custom_configs.append(
                    ConfigInfo(
                        id=config.id,
                        name=config.name,
                        description=config.description,
                        version=config.version,
                        allowed_tools=config.allowed_tools,
                        has_mcp_servers=bool(config.mcp_servers),
                        has_sub_agents=bool(config.agents),
                        permission_mode=config.permission_mode,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to load custom config {config_file}: {e}")
                continue

        return ConfigListResponse(configs=custom_configs, total=len(custom_configs))

    except Exception as e:
        logger.error(f"Failed to list custom configs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list custom configs: {str(e)}")


@router.delete("/custom/{config_id}")
async def delete_custom_config(config_id: str):
    """
    Delete a custom user-created configuration

    Args:
        config_id: Configuration ID to delete

    Returns:
        Success status
    """
    try:
        config_file = Path.home() / ".agcluster" / "configs" / "custom" / f"{config_id}.yaml"

        if not config_file.exists():
            raise HTTPException(status_code=404, detail=f"Custom config '{config_id}' not found")

        config_file.unlink()
        logger.info(f"Deleted custom config: {config_id}")

        return {"status": "success", "config_id": config_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete custom config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {str(e)}")
