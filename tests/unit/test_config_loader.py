"""Tests for configuration loading utility"""

import pytest
import yaml
from agcluster.container.core.config_loader import (
    load_config_from_file,
    load_config_from_id,
    list_available_configs,
    ConfigNotFoundError,
)
from agcluster.container.models.agent_config import AgentConfig


class TestLoadConfigFromFile:
    """Test loading config from YAML file"""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML configuration"""
        config_file = tmp_path / "test-config.yaml"
        config_data = {"id": "test-agent", "name": "Test Agent", "allowed_tools": ["Bash", "Read"]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config_from_file(config_file)

        assert isinstance(config, AgentConfig)
        assert config.id == "test-agent"
        assert config.name == "Test Agent"
        assert "Bash" in config.allowed_tools

    def test_load_config_with_sub_agents(self, tmp_path):
        """Test loading config with sub-agents"""
        config_file = tmp_path / "team-config.yaml"
        config_data = {
            "id": "team",
            "name": "Team",
            "allowed_tools": ["Task"],
            "agents": {
                "frontend": {
                    "description": "Frontend dev",
                    "prompt": "You are a frontend specialist",
                    "tools": ["Read", "Write"],
                }
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config_from_file(config_file)

        assert "frontend" in config.agents
        assert config.agents["frontend"].description == "Frontend dev"

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error"""
        config_file = tmp_path / "invalid.yaml"

        with open(config_file, "w") as f:
            f.write("invalid: yaml: content:")

        with pytest.raises(yaml.YAMLError):
            load_config_from_file(config_file)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/file.yaml")

    def test_load_invalid_config_schema(self, tmp_path):
        """Test loading YAML with invalid schema"""
        config_file = tmp_path / "invalid-schema.yaml"
        config_data = {
            "id": "test",
            "name": "Test",
            "allowed_tools": ["InvalidTool"],  # Invalid tool name
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError):
            load_config_from_file(config_file)

    def test_auto_load_extra_files(self, tmp_path):
        """Test auto-loading extra files from directory with same name as config"""
        # Create config file
        config_file = tmp_path / "test-agent.yaml"
        config_data = {"id": "test-agent", "name": "Test Agent", "allowed_tools": ["Bash", "Read"]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create directory with same name and add files
        extra_files_dir = tmp_path / "test-agent"
        extra_files_dir.mkdir()

        # Create some test files
        (extra_files_dir / "file1.txt").write_text("content1")
        (extra_files_dir / "file2.py").write_text("print('hello')")

        # Create subdirectory with file
        subdir = extra_files_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("# Nested file")

        # Load config
        config = load_config_from_file(config_file)

        # Verify extra files were loaded
        assert config.extra_files is not None
        assert len(config.extra_files) == 3

        # Check file paths and contents
        assert "file1.txt" in config.extra_files
        assert config.extra_files["file1.txt"] == b"content1"

        assert "file2.py" in config.extra_files
        assert config.extra_files["file2.py"] == b"print('hello')"

        assert "subdir/nested.md" in config.extra_files or "subdir\\nested.md" in config.extra_files

    def test_no_extra_files_directory(self, tmp_path):
        """Test that config loads normally when no extra files directory exists"""
        config_file = tmp_path / "simple-agent.yaml"
        config_data = {"id": "simple-agent", "name": "Simple Agent", "allowed_tools": ["Bash"]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # No extra files directory created

        config = load_config_from_file(config_file)

        # Should load successfully without extra_files
        assert config.id == "simple-agent"
        assert config.extra_files is None or len(config.extra_files) == 0

    def test_empty_extra_files_directory(self, tmp_path):
        """Test handling of empty extra files directory"""
        config_file = tmp_path / "empty-agent.yaml"
        config_data = {"id": "empty-agent", "name": "Empty Agent", "allowed_tools": ["Bash"]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create empty directory
        extra_files_dir = tmp_path / "empty-agent"
        extra_files_dir.mkdir()

        config = load_config_from_file(config_file)

        # Should not have extra_files if directory is empty
        assert config.extra_files is None or len(config.extra_files) == 0


class TestLoadConfigFromId:
    """Test loading config by ID"""

    def test_load_preset_config(self):
        """Test loading built-in preset configuration"""
        # Should load from configs/presets/code-assistant.yaml
        config = load_config_from_id("code-assistant")

        assert config.id == "code-assistant"
        assert config.name == "Code Assistant"
        assert "Bash" in config.allowed_tools

    def test_load_research_agent_preset(self):
        """Test loading research agent preset"""
        config = load_config_from_id("research-agent")

        assert config.id == "research-agent"
        assert "WebFetch" in config.allowed_tools
        assert "WebSearch" in config.allowed_tools

    def test_load_multiagent_preset(self):
        """Test loading multi-agent preset"""
        config = load_config_from_id("fullstack-team")

        assert config.id == "fullstack-team"
        assert config.agents is not None
        assert "frontend" in config.agents
        assert "backend" in config.agents
        assert "devops" in config.agents

    def test_load_nonexistent_config_id(self):
        """Test loading non-existent config ID"""
        with pytest.raises(ConfigNotFoundError) as exc_info:
            load_config_from_id("nonexistent-config")

        assert "nonexistent-config" in str(exc_info.value)

    def test_load_user_config(self, tmp_path):
        """Test loading user config from ~/.agcluster/configs/"""
        # Mock the user config directory
        user_config_dir = tmp_path / ".agcluster" / "configs"
        user_config_dir.mkdir(parents=True)

        config_file = user_config_dir / "my-agent.yaml"
        config_data = {
            "id": "my-agent",
            "name": "My Custom Agent",
            "allowed_tools": ["Read", "Write"],
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Pass user_config_dir explicitly
        config = load_config_from_id("my-agent", user_config_dir=user_config_dir)

        assert config.id == "my-agent"
        assert config.name == "My Custom Agent"


class TestListAvailableConfigs:
    """Test listing available configurations"""

    def test_list_preset_configs(self):
        """Test listing built-in preset configs"""
        configs = list_available_configs()

        assert len(configs) >= 3  # At least our 3 presets
        config_ids = [c.id for c in configs]

        assert "code-assistant" in config_ids
        assert "research-agent" in config_ids
        assert "fullstack-team" in config_ids

    def test_list_includes_user_configs(self, tmp_path):
        """Test that list includes user configs"""
        user_config_dir = tmp_path / ".agcluster" / "configs"
        user_config_dir.mkdir(parents=True)

        # Create user config
        config_file = user_config_dir / "custom.yaml"
        config_data = {"id": "custom", "name": "Custom", "allowed_tools": ["Bash"]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Pass user_config_dir explicitly
        configs = list_available_configs(user_config_dir=user_config_dir)
        config_ids = [c.id for c in configs]

        assert "custom" in config_ids

    def test_list_configs_returns_agent_config_objects(self):
        """Test that list returns proper AgentConfig objects"""
        configs = list_available_configs()

        for config in configs:
            assert isinstance(config, AgentConfig)
            assert config.id
            assert config.name

    def test_list_configs_handles_invalid_files(self, tmp_path, monkeypatch):
        """Test that list handles invalid config files gracefully"""
        preset_dir = tmp_path / "configs" / "presets"
        preset_dir.mkdir(parents=True)

        # Valid config
        valid_file = preset_dir / "valid.yaml"
        with open(valid_file, "w") as f:
            yaml.dump({"id": "valid", "name": "Valid"}, f)

        # Invalid config
        invalid_file = preset_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid yaml content::")

        # Should only return valid configs, skip invalid
        monkeypatch.setattr("agcluster.container.core.config_loader.PRESET_DIR", preset_dir)

        configs = list_available_configs()

        # Should have valid config, invalid should be skipped
        assert len(configs) >= 1
        assert any(c.id == "valid" for c in configs)
