"""Configuration loading utilities"""

import yaml
import logging
from pathlib import Path
from typing import List, Union
from agcluster.container.models.agent_config import AgentConfig

logger = logging.getLogger(__name__)

# Configuration directories
PRESET_DIR = Path(__file__).parent.parent.parent.parent.parent / "configs" / "presets"
USER_CONFIG_DIR = Path.home() / ".agcluster" / "configs"


class ConfigNotFoundError(Exception):
    """Raised when a configuration cannot be found"""
    pass


def load_config_from_file(file_path: Union[str, Path]) -> AgentConfig:
    """
    Load agent configuration from YAML file

    Args:
        file_path: Path to YAML configuration file

    Returns:
        AgentConfig object

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
        ValueError: If config schema is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    logger.info(f"Loading config from {file_path}")

    try:
        with open(file_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Validate and create AgentConfig
        config = AgentConfig(**config_data)

        logger.info(f"Successfully loaded config: {config.id}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {file_path}: {e}")
        raise

    except Exception as e:
        logger.error(f"Invalid config schema in {file_path}: {e}")
        raise ValueError(f"Invalid configuration: {e}")


def load_config_from_id(config_id: str, user_config_dir: Path = None) -> AgentConfig:
    """
    Load agent configuration by ID

    Searches for config in:
    1. User configs (~/.agcluster/configs/)
    2. Preset configs (configs/presets/)

    Args:
        config_id: Configuration ID
        user_config_dir: Optional override for user config directory (for testing)

    Returns:
        AgentConfig object

    Raises:
        ConfigNotFoundError: If config ID not found
    """
    logger.info(f"Loading config by ID: {config_id}")

    if user_config_dir is None:
        user_config_dir = USER_CONFIG_DIR

    # Try user config directory first
    user_config_file = user_config_dir / f"{config_id}.yaml"
    if user_config_file.exists():
        logger.info(f"Found user config: {user_config_file}")
        return load_config_from_file(user_config_file)

    # Try preset directory
    preset_config_file = PRESET_DIR / f"{config_id}.yaml"
    if preset_config_file.exists():
        logger.info(f"Found preset config: {preset_config_file}")
        return load_config_from_file(preset_config_file)

    # Config not found
    raise ConfigNotFoundError(
        f"Configuration '{config_id}' not found in user configs or presets"
    )


def list_available_configs(user_config_dir: Path = None) -> List[AgentConfig]:
    """
    List all available agent configurations

    Args:
        user_config_dir: Optional override for user config directory (for testing)

    Returns:
        List of AgentConfig objects from both presets and user configs
    """
    configs = []

    if user_config_dir is None:
        user_config_dir = USER_CONFIG_DIR

    # Load preset configs
    if PRESET_DIR.exists():
        logger.info(f"Scanning preset configs in {PRESET_DIR}")
        for config_file in PRESET_DIR.glob("*.yaml"):
            try:
                config = load_config_from_file(config_file)
                configs.append(config)
                logger.debug(f"Loaded preset: {config.id}")
            except Exception as e:
                logger.warning(f"Skipping invalid config {config_file}: {e}")

    # Load user configs
    if user_config_dir.exists():
        logger.info(f"Scanning user configs in {user_config_dir}")
        for config_file in user_config_dir.glob("*.yaml"):
            try:
                config = load_config_from_file(config_file)
                configs.append(config)
                logger.debug(f"Loaded user config: {config.id}")
            except Exception as e:
                logger.warning(f"Skipping invalid config {config_file}: {e}")

    logger.info(f"Loaded {len(configs)} configurations")
    return configs


def get_config_search_paths() -> List[Path]:
    """
    Get list of directories searched for configurations

    Returns:
        List of Path objects
    """
    return [USER_CONFIG_DIR, PRESET_DIR]
