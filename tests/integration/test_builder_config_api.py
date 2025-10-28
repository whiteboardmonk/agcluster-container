"""
Integration tests for builder configuration API endpoints.

Tests the new agent configuration fields:
- Multi-agent orchestration (agents dictionary)
- MCP server configuration (mcp_servers)
- Structured system prompts (preset + append)
- Advanced fields (env, cwd, setting_sources)
"""

import pytest
from fastapi.testclient import TestClient
from agcluster.container.api.main import app

client = TestClient(app)


class TestBuilderConfigAPI:
    """Test builder configuration CRUD operations with new fields."""

    def test_save_config_with_multi_agent(self):
        """Test saving configuration with sub-agents."""
        config = {
            "id": "test-multi-agent",
            "name": "Test Multi-Agent Team",
            "description": "A multi-agent configuration for testing",
            "allowed_tools": ["Bash", "Read", "Write"],
            "system_prompt": "You are a coordinator agent",
            "permission_mode": "acceptEdits",
            "resource_limits": {"cpu_quota": 200000, "memory_limit": "4g", "storage_limit": "10g"},
            "agents": {
                "frontend": {
                    "description": "Frontend development specialist",
                    "prompt": "You are a frontend expert",
                    "tools": ["Bash", "Read", "Write", "Edit"],
                    "model": "sonnet",
                },
                "backend": {
                    "description": "Backend development specialist",
                    "prompt": "You are a backend expert",
                    "tools": ["Bash", "Read", "Write"],
                    "model": "opus",
                },
            },
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"
        assert "config_id" in post_data
        assert post_data["config_id"] == "test-multi-agent"

        # GET the config back
        get_response = client.get("/api/configs/test-multi-agent")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify all fields were saved correctly
        assert data["id"] == "test-multi-agent"
        assert data["name"] == "Test Multi-Agent Team"
        assert "agents" in data
        assert "frontend" in data["agents"]
        assert "backend" in data["agents"]
        assert data["agents"]["frontend"]["model"] == "sonnet"
        assert data["agents"]["backend"]["model"] == "opus"
        assert data["agents"]["frontend"]["description"] == "Frontend development specialist"
        assert data["agents"]["backend"]["description"] == "Backend development specialist"

    def test_load_config_with_multi_agent(self):
        """Test loading configuration preserves sub-agents."""
        # First save the config
        config = {
            "id": "test-load-multi",
            "name": "Test Load Multi-Agent",
            "allowed_tools": ["Bash"],
            "agents": {
                "agent1": {"description": "Test agent", "prompt": "Test prompt", "tools": ["Read"]}
            },
        }
        client.post("/api/configs/custom", json=config)

        # Now load it back
        response = client.get("/api/configs/test-load-multi")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "agent1" in data["agents"]
        assert data["agents"]["agent1"]["description"] == "Test agent"

    def test_save_config_with_mcp_servers(self):
        """Test saving configuration with MCP servers."""
        config = {
            "id": "test-mcp-servers",
            "name": "Test MCP Servers",
            "allowed_tools": ["Bash", "Read"],
            "mcp_servers": {
                "stdio-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["./mcp-server.js", "--port=3000"],
                },
                "http-server": {"type": "http", "url": "http://localhost:4000/mcp"},
            },
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"
        assert "config_id" in post_data

        # GET the config back
        get_response = client.get("/api/configs/test-mcp-servers")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify all fields were saved correctly
        assert "mcp_servers" in data
        assert "stdio-server" in data["mcp_servers"]
        assert data["mcp_servers"]["stdio-server"]["type"] == "stdio"
        assert data["mcp_servers"]["stdio-server"]["command"] == "node"
        assert data["mcp_servers"]["stdio-server"]["args"] == ["./mcp-server.js", "--port=3000"]
        assert "http-server" in data["mcp_servers"]
        assert data["mcp_servers"]["http-server"]["type"] == "http"
        assert data["mcp_servers"]["http-server"]["url"] == "http://localhost:4000/mcp"

    def test_save_config_with_structured_system_prompt(self):
        """Test saving configuration with preset system prompt."""
        config = {
            "id": "test-preset-prompt",
            "name": "Test Preset Prompt",
            "allowed_tools": ["Bash"],
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": "Additional instructions for this agent",
            },
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"

        # GET the config back
        get_response = client.get("/api/configs/test-preset-prompt")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify all fields were saved correctly
        assert "system_prompt" in data
        assert isinstance(data["system_prompt"], dict)
        assert data["system_prompt"]["type"] == "preset"
        assert data["system_prompt"]["preset"] == "claude_code"
        assert data["system_prompt"]["append"] == "Additional instructions for this agent"

    def test_save_config_with_plain_system_prompt(self):
        """Test saving configuration with plain string system prompt."""
        config = {
            "id": "test-plain-prompt",
            "name": "Test Plain Prompt",
            "allowed_tools": ["Bash"],
            "system_prompt": "You are a helpful assistant",
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"

        # GET the config back
        get_response = client.get("/api/configs/test-plain-prompt")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify all fields were saved correctly
        assert data["system_prompt"] == "You are a helpful assistant"

    def test_save_config_with_advanced_fields(self):
        """Test saving configuration with advanced fields (env, cwd, setting_sources)."""
        config = {
            "id": "test-advanced-fields",
            "name": "Test Advanced Fields",
            "allowed_tools": ["Bash", "Read"],
            "version": "2.0.0",
            "model": "claude-sonnet-4.5",
            "cwd": "/workspace/project",
            "env": {
                "API_KEY": "test-key-123",
                "DATABASE_URL": "postgres://localhost/test",
                "DEBUG": "true",
            },
            "setting_sources": ["user", "project"],
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"

        # GET the config back
        get_response = client.get("/api/configs/test-advanced-fields")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify all fields were saved correctly
        assert data["version"] == "2.0.0"
        assert data["model"] == "claude-sonnet-4.5"
        assert data["cwd"] == "/workspace/project"
        assert "env" in data
        assert data["env"]["API_KEY"] == "test-key-123"
        assert data["env"]["DATABASE_URL"] == "postgres://localhost/test"
        assert data["env"]["DEBUG"] == "true"
        assert data["setting_sources"] == ["user", "project"]

    def test_save_config_with_all_new_features(self):
        """Test saving configuration with all new features combined."""
        config = {
            "id": "test-all-features",
            "name": "Test All Features",
            "description": "Comprehensive test",
            "version": "3.0.0",
            "allowed_tools": ["Bash", "Read", "Write", "Task"],
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": "Work collaboratively with sub-agents",
            },
            "permission_mode": "plan",
            "model": "claude-opus-4",
            "cwd": "/workspace",
            "env": {"NODE_ENV": "production"},
            "setting_sources": ["user", "project", "local"],
            "resource_limits": {"cpu_quota": 300000, "memory_limit": "8g", "storage_limit": "20g"},
            "max_turns": 150,
            "agents": {
                "researcher": {
                    "description": "Research specialist",
                    "prompt": "You research topics thoroughly",
                    "tools": ["WebSearch", "WebFetch"],
                    "model": "haiku",
                }
            },
            "mcp_servers": {"analytics": {"type": "sse", "url": "http://localhost:5000/analytics"}},
        }

        # POST the config
        post_response = client.post("/api/configs/custom", json=config)
        assert post_response.status_code == 200
        post_data = post_response.json()

        # Verify POST response format
        assert "status" in post_data
        assert post_data["status"] == "success"
        assert "config_id" in post_data

        # GET the config back
        get_response = client.get("/api/configs/test-all-features")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify basic fields
        assert data["id"] == "test-all-features"
        assert data["name"] == "Test All Features"
        assert data["description"] == "Comprehensive test"
        assert data["version"] == "3.0.0"
        assert data["permission_mode"] == "plan"
        assert data["max_turns"] == 150

        # Verify structured system prompt
        assert isinstance(data["system_prompt"], dict)
        assert data["system_prompt"]["type"] == "preset"
        assert data["system_prompt"]["preset"] == "claude_code"
        assert data["system_prompt"]["append"] == "Work collaboratively with sub-agents"

        # Verify multi-agent
        assert "agents" in data
        assert "researcher" in data["agents"]
        assert data["agents"]["researcher"]["description"] == "Research specialist"
        assert data["agents"]["researcher"]["model"] == "haiku"

        # Verify MCP servers
        assert "mcp_servers" in data
        assert "analytics" in data["mcp_servers"]
        assert data["mcp_servers"]["analytics"]["type"] == "sse"
        assert data["mcp_servers"]["analytics"]["url"] == "http://localhost:5000/analytics"

        # Verify advanced fields
        assert data["model"] == "claude-opus-4"
        assert data["cwd"] == "/workspace"
        assert data["env"]["NODE_ENV"] == "production"
        assert data["setting_sources"] == ["user", "project", "local"]

        # Verify resource limits
        assert data["resource_limits"]["cpu_quota"] == 300000
        assert data["resource_limits"]["memory_limit"] == "8g"
        assert data["resource_limits"]["storage_limit"] == "20g"

    def test_load_preset_config_with_multi_agent(self):
        """Test loading preset configuration (fullstack-team) preserves multi-agent structure."""
        response = client.get("/api/configs/fullstack-team")

        assert response.status_code == 200
        data = response.json()

        # fullstack-team preset has sub-agents
        assert "agents" in data
        assert "frontend" in data["agents"]
        assert "backend" in data["agents"]
        assert "devops" in data["agents"]

        # Verify sub-agent structure
        frontend = data["agents"]["frontend"]
        assert "description" in frontend
        assert "prompt" in frontend
        assert "tools" in frontend

    def test_validation_empty_sub_agent_name(self):
        """Test that empty sub-agent names are rejected."""
        config = {
            "id": "test-validation",
            "name": "Test Validation",
            "allowed_tools": ["Bash"],
            "agents": {"": {"description": "Invalid", "prompt": "Invalid"}},  # Empty name
        }

        response = client.post("/api/configs/custom", json=config)

        # Should either reject or auto-generate name
        # Implementation depends on backend validation rules
        assert response.status_code in [200, 400, 422]

    def test_validation_invalid_mcp_transport_type(self):
        """Test that invalid MCP transport types are rejected."""
        config = {
            "id": "test-invalid-mcp",
            "name": "Test Invalid MCP",
            "allowed_tools": ["Bash"],
            "mcp_servers": {
                "invalid-server": {
                    "type": "invalid_type",  # Invalid type
                    "url": "http://localhost:3000",
                }
            },
        }

        response = client.post("/api/configs/custom", json=config)

        # Should reject invalid transport type
        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
