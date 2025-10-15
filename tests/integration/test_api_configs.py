"""Integration tests for config API endpoints"""

import pytest
from fastapi.testclient import TestClient
from agcluster.container.api.main import app

client = TestClient(app)


class TestConfigsEndpoints:
    """Test /api/configs endpoints"""

    def test_list_configs(self):
        """Should list all available configs"""
        response = client.get("/api/configs/")

        assert response.status_code == 200
        data = response.json()

        assert "configs" in data
        assert "total" in data
        assert isinstance(data["configs"], list)
        assert data["total"] >= 3  # At least our 3 presets

        # Check preset IDs are included
        config_ids = [c["id"] for c in data["configs"]]
        assert "code-assistant" in config_ids
        assert "research-agent" in config_ids
        assert "fullstack-team" in config_ids

    def test_get_config_by_id(self):
        """Should get specific config by ID"""
        response = client.get("/api/configs/code-assistant")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "code-assistant"
        assert data["name"] == "Code Assistant"
        assert "allowed_tools" in data
        assert isinstance(data["allowed_tools"], list)
        assert "Bash" in data["allowed_tools"]

    def test_get_nonexistent_config(self):
        """Should return 404 for non-existent config"""
        response = client.get("/api/configs/nonexistent-config")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "nonexistent-config" in data["detail"]

    def test_config_info_structure(self):
        """Should return proper ConfigInfo structure"""
        response = client.get("/api/configs/")
        data = response.json()

        config = data["configs"][0]
        assert "id" in config
        assert "name" in config
        assert "allowed_tools" in config
        assert "has_mcp_servers" in config
        assert "has_sub_agents" in config
        assert isinstance(config["has_mcp_servers"], bool)
        assert isinstance(config["has_sub_agents"], bool)

    def test_multiagent_config_flags(self):
        """Should correctly set has_sub_agents flag"""
        response = client.get("/api/configs/fullstack-team")
        data = response.json()

        # Fullstack team has sub-agents
        assert data["id"] == "fullstack-team"
        assert "agents" in data
        assert isinstance(data["agents"], dict)
        assert len(data["agents"]) > 0
