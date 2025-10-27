"""Tests for agent configuration models"""

import pytest
from pydantic import ValidationError
from agcluster.container.models.agent_config import (
    AgentConfig,
    AgentDefinition,
    ResourceLimits,
    SystemPromptPreset,
    McpStdioServerConfig,
    McpSseServerConfig,
    McpHttpServerConfig,
)


class TestAgentConfig:
    """Test AgentConfig model validation"""

    def test_minimal_config(self):
        """Test minimal valid configuration"""
        config = AgentConfig(id="test-agent", name="Test Agent")

        assert config.id == "test-agent"
        assert config.name == "Test Agent"
        assert config.allowed_tools == []
        assert config.mcp_servers == {}
        assert config.version == "1.0.0"

    def test_full_config(self):
        """Test full configuration with all fields"""
        config = AgentConfig(
            id="code-assistant",
            name="Code Assistant",
            description="Full-stack development agent",
            version="2.0.0",
            allowed_tools=["Bash", "Read", "Write", "Edit"],
            system_prompt="You are a helpful assistant",
            permission_mode="acceptEdits",
            resource_limits=ResourceLimits(
                cpu_quota=200000, memory_limit="4g", storage_limit="10g"
            ),
            max_turns=50,
            model="claude-sonnet-4.5",
            cwd="/workspace",
            env={"DEBUG": "true"},
        )

        assert config.id == "code-assistant"
        assert len(config.allowed_tools) == 4
        assert config.permission_mode == "acceptEdits"
        assert config.resource_limits.cpu_quota == 200000
        assert config.resource_limits.memory_limit == "4g"

    def test_system_prompt_as_string(self):
        """Test system prompt as plain string"""
        config = AgentConfig(id="test", name="Test", system_prompt="Custom prompt")

        assert config.system_prompt == "Custom prompt"

    def test_system_prompt_as_preset(self):
        """Test system prompt using preset"""
        config = AgentConfig(
            id="test",
            name="Test",
            system_prompt=SystemPromptPreset(
                type="preset", preset="claude_code", append="Additional instructions"
            ),
        )

        assert isinstance(config.system_prompt, SystemPromptPreset)
        assert config.system_prompt.preset == "claude_code"
        assert config.system_prompt.append == "Additional instructions"

    def test_invalid_tool_name(self):
        """Test validation rejects invalid tool names"""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(id="test", name="Test", allowed_tools=["InvalidTool"])

        assert "Invalid tool" in str(exc_info.value)

    def test_valid_tool_names(self):
        """Test all valid built-in tool names"""
        valid_tools = [
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
        ]

        config = AgentConfig(id="test", name="Test", allowed_tools=valid_tools)

        assert len(config.allowed_tools) == len(valid_tools)

    def test_mcp_tool_names_allowed(self):
        """Test MCP tool names (mcp__server__tool format)"""
        config = AgentConfig(
            id="test",
            name="Test",
            allowed_tools=["Bash", "mcp__github__create_issue", "mcp__slack__send_message"],
        )

        assert "mcp__github__create_issue" in config.allowed_tools
        assert "mcp__slack__send_message" in config.allowed_tools

    def test_invalid_config_id_format(self):
        """Test config ID validation"""
        # Empty ID
        with pytest.raises(ValidationError):
            AgentConfig(id="", name="Test")

        # Uppercase not allowed
        with pytest.raises(ValidationError):
            AgentConfig(id="Code-Assistant", name="Test")

        # Special characters not allowed
        with pytest.raises(ValidationError):
            AgentConfig(id="code@assistant", name="Test")

    def test_valid_config_id_formats(self):
        """Test valid config ID formats"""
        valid_ids = ["test", "test-agent", "test_agent", "agent-1", "agent_v2"]

        for config_id in valid_ids:
            config = AgentConfig(id=config_id, name="Test")
            assert config.id == config_id

    def test_permission_modes(self):
        """Test all valid permission modes"""
        modes = ["default", "acceptEdits", "plan", "bypassPermissions"]

        for mode in modes:
            config = AgentConfig(id="test", name="Test", permission_mode=mode)
            assert config.permission_mode == mode

    def test_invalid_permission_mode(self):
        """Test invalid permission mode is rejected"""
        with pytest.raises(ValidationError):
            AgentConfig(id="test", name="Test", permission_mode="invalid_mode")


class TestAgentDefinition:
    """Test AgentDefinition model for sub-agents"""

    def test_minimal_agent_definition(self):
        """Test minimal sub-agent definition"""
        agent = AgentDefinition(
            description="Frontend specialist", prompt="You are a frontend developer"
        )

        assert agent.description == "Frontend specialist"
        assert agent.prompt == "You are a frontend developer"
        assert agent.tools is None
        assert agent.model is None

    def test_full_agent_definition(self):
        """Test full sub-agent definition"""
        agent = AgentDefinition(
            description="Backend specialist",
            prompt="You are a backend developer",
            tools=["Read", "Write", "Bash"],
            model="haiku",
        )

        assert len(agent.tools) == 3
        assert agent.model == "haiku"

    def test_agent_model_options(self):
        """Test valid model options for sub-agents"""
        models = ["sonnet", "opus", "haiku", "inherit"]

        for model in models:
            agent = AgentDefinition(description="Test", prompt="Test", model=model)
            assert agent.model == model


class TestMultiAgentConfig:
    """Test multi-agent configuration"""

    def test_config_with_subagents(self):
        """Test configuration with multiple sub-agents"""
        config = AgentConfig(
            id="fullstack-team",
            name="Full-Stack Team",
            allowed_tools=["Task", "Read"],  # Orchestrator tools
            agents={
                "frontend": AgentDefinition(
                    description="Frontend development",
                    prompt="You specialize in React",
                    tools=["Read", "Write", "Edit"],
                ),
                "backend": AgentDefinition(
                    description="Backend development",
                    prompt="You specialize in Python",
                    tools=["Read", "Write", "Bash"],
                ),
            },
        )

        assert len(config.agents) == 2
        assert "frontend" in config.agents
        assert "backend" in config.agents
        assert config.agents["frontend"].tools == ["Read", "Write", "Edit"]


class TestMcpServerConfig:
    """Test MCP server configuration models"""

    def test_stdio_server_minimal(self):
        """Test minimal stdio MCP server config"""
        server = McpStdioServerConfig(command="npx")

        assert server.type == "stdio"
        assert server.command == "npx"
        assert server.args is None
        assert server.env is None

    def test_stdio_server_full(self):
        """Test full stdio MCP server config"""
        server = McpStdioServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "secret"},
        )

        assert len(server.args) == 2
        assert "GITHUB_TOKEN" in server.env

    def test_sse_server(self):
        """Test SSE MCP server config"""
        server = McpSseServerConfig(
            type="sse", url="https://example.com/mcp", headers={"Authorization": "Bearer token"}
        )

        assert server.type == "sse"
        assert server.url == "https://example.com/mcp"
        assert server.headers["Authorization"] == "Bearer token"

    def test_http_server(self):
        """Test HTTP MCP server config"""
        server = McpHttpServerConfig(type="http", url="https://api.example.com/mcp")

        assert server.type == "http"
        assert server.url == "https://api.example.com/mcp"

    def test_config_with_mcp_servers(self):
        """Test agent config with multiple MCP servers"""
        config = AgentConfig(
            id="test",
            name="Test",
            mcp_servers={
                "github": McpStdioServerConfig(
                    command="npx", args=["-y", "@modelcontextprotocol/server-github"]
                ),
                "slack": McpSseServerConfig(type="sse", url="https://slack.com/mcp"),
            },
            allowed_tools=["mcp__github__create_issue", "mcp__slack__send_message"],
        )

        assert len(config.mcp_servers) == 2
        assert "github" in config.mcp_servers
        assert "slack" in config.mcp_servers
        assert config.mcp_servers["github"].command == "npx"


class TestResourceLimits:
    """Test resource limits configuration"""

    def test_cpu_quota(self):
        """Test CPU quota configuration"""
        limits = ResourceLimits(cpu_quota=200000)
        assert limits.cpu_quota == 200000

    def test_memory_limit(self):
        """Test memory limit configuration"""
        limits = ResourceLimits(memory_limit="4g")
        assert limits.memory_limit == "4g"

    def test_all_limits(self):
        """Test all resource limits"""
        limits = ResourceLimits(cpu_quota=200000, memory_limit="4g", storage_limit="10g")

        assert limits.cpu_quota == 200000
        assert limits.memory_limit == "4g"
        assert limits.storage_limit == "10g"


class TestConfigSerialization:
    """Test JSON serialization/deserialization"""

    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = AgentConfig(
            id="test",
            name="Test Agent",
            allowed_tools=["Bash", "Read"],
            permission_mode="acceptEdits",
        )

        config_dict = config.model_dump()

        assert config_dict["id"] == "test"
        assert config_dict["name"] == "Test Agent"
        assert "Bash" in config_dict["allowed_tools"]

    def test_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            "id": "test",
            "name": "Test Agent",
            "allowed_tools": ["Bash", "Read"],
            "permission_mode": "acceptEdits",
            "resource_limits": {"cpu_quota": 200000, "memory_limit": "4g"},
        }

        config = AgentConfig(**config_dict)

        assert config.id == "test"
        assert len(config.allowed_tools) == 2
        assert config.resource_limits.cpu_quota == 200000

    def test_json_serialization(self):
        """Test JSON serialization"""
        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        json_str = config.model_dump_json()
        assert "test" in json_str
        assert "Bash" in json_str

    def test_complex_config_round_trip(self):
        """Test complex config serialization round trip"""
        original = AgentConfig(
            id="fullstack",
            name="Full-Stack",
            allowed_tools=["Task", "Read", "Write"],
            system_prompt=SystemPromptPreset(
                type="preset", preset="claude_code", append="Follow TDD"
            ),
            mcp_servers={
                "github": McpStdioServerConfig(
                    command="npx", args=["-y", "@modelcontextprotocol/server-github"]
                )
            },
            agents={
                "frontend": AgentDefinition(
                    description="Frontend", prompt="React specialist", tools=["Read", "Write"]
                )
            },
        )

        # Serialize to dict and back
        config_dict = original.model_dump()
        restored = AgentConfig(**config_dict)

        assert restored.id == original.id
        assert restored.name == original.name
        assert len(restored.allowed_tools) == len(original.allowed_tools)
        assert "github" in restored.mcp_servers
        assert "frontend" in restored.agents
