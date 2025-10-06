"""Configuration settings for AgCluster"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Docker Settings
    docker_network: str = "bridge"
    agent_image: str = "agcluster/agent:latest"

    # Container Resource Limits
    container_cpu_quota: int = 200000  # 2 CPUs
    container_memory_limit: str = "4g"
    container_storage_limit: str = "10g"

    # Agent Defaults
    default_system_prompt: str = "You are a helpful AI assistant with access to tools."
    default_allowed_tools: str = "Bash,Read,Write,Grep"

    # Container Cleanup
    inactive_container_timeout: int = 1800  # 30 minutes in seconds

    # Logging
    log_level: str = "info"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
