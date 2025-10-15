"""Unit tests for session manager"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from agcluster.container.core.session_manager import SessionManager, SessionNotFoundError
from agcluster.container.core.container_manager import AgentContainer
from agcluster.container.models.agent_config import AgentConfig


@pytest.fixture
def mock_container_manager():
    """Mock container manager"""
    with patch('agcluster.container.core.session_manager.container_manager') as mock:
        # Create a mock container
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent-123"
        mock_container.last_active = datetime.now(timezone.utc)

        # Mock create_agent_container to return the mock container
        mock.create_agent_container = AsyncMock(return_value=mock_container)
        mock.stop_container = AsyncMock()

        yield mock


@pytest.fixture
def session_mgr():
    """Create a session manager with short timeout for testing"""
    return SessionManager(idle_timeout_minutes=1)


class TestSessionIDGeneration:
    """Test session ID generation logic"""

    def test_generate_session_id_with_conversation_id(self, session_mgr):
        """Should use conversation ID when provided"""
        session_id = session_mgr._generate_session_id("conv-123", "sk-ant-test-key")
        assert session_id == "conv-conv-123"

    def test_generate_session_id_without_conversation_id(self, session_mgr):
        """Should hash API key when no conversation ID"""
        session_id = session_mgr._generate_session_id(None, "sk-ant-test-key")
        assert session_id.startswith("user-")
        assert len(session_id) > 5  # user- + hash

    def test_generate_session_id_same_key_same_id(self, session_mgr):
        """Same API key should generate same session ID"""
        id1 = session_mgr._generate_session_id(None, "sk-ant-test-key")
        id2 = session_mgr._generate_session_id(None, "sk-ant-test-key")
        assert id1 == id2

    def test_generate_session_id_different_keys_different_ids(self, session_mgr):
        """Different API keys should generate different session IDs"""
        id1 = session_mgr._generate_session_id(None, "sk-ant-key-1")
        id2 = session_mgr._generate_session_id(None, "sk-ant-key-2")
        assert id1 != id2


class TestGetOrCreateSession:
    """Test session retrieval and creation"""

    @pytest.mark.asyncio
    async def test_create_new_session(self, session_mgr, mock_container_manager):
        """Should create new session when none exists"""
        container = await session_mgr.get_or_create_session(
            conversation_id="conv-new",
            api_key="sk-ant-test-key"
        )

        assert container.agent_id == "test-agent-123"
        assert "conv-conv-new" in session_mgr.sessions
        mock_container_manager.create_agent_container.assert_called_once()

    @pytest.mark.asyncio
    async def test_reuse_existing_session(self, session_mgr, mock_container_manager):
        """Should reuse existing session for same conversation"""
        # Create first session
        container1 = await session_mgr.get_or_create_session(
            conversation_id="conv-reuse",
            api_key="sk-ant-test-key"
        )

        # Get same session again
        container2 = await session_mgr.get_or_create_session(
            conversation_id="conv-reuse",
            api_key="sk-ant-test-key"
        )

        assert container1 == container2
        # Should only create container once
        assert mock_container_manager.create_agent_container.call_count == 1

    @pytest.mark.asyncio
    async def test_update_last_active_on_reuse(self, session_mgr, mock_container_manager):
        """Should update last_active when reusing session"""
        # Create session
        container = await session_mgr.get_or_create_session(
            conversation_id="conv-active",
            api_key="sk-ant-test-key"
        )

        original_time = container.last_active

        # Wait a bit
        await asyncio.sleep(0.1)

        # Reuse session
        await session_mgr.get_or_create_session(
            conversation_id="conv-active",
            api_key="sk-ant-test-key"
        )

        # last_active should be updated
        assert container.last_active > original_time

    @pytest.mark.asyncio
    async def test_different_conversations_different_sessions(self, session_mgr, mock_container_manager):
        """Different conversations should get different sessions"""
        # Need to return different containers for different calls
        container1 = Mock(spec=AgentContainer)
        container1.agent_id = "agent-1"
        container1.last_active = datetime.now(timezone.utc)

        container2 = Mock(spec=AgentContainer)
        container2.agent_id = "agent-2"
        container2.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container.side_effect = [container1, container2]

        # Create two different sessions
        c1 = await session_mgr.get_or_create_session("conv-1", "sk-ant-key")
        c2 = await session_mgr.get_or_create_session("conv-2", "sk-ant-key")

        assert c1.agent_id != c2.agent_id
        assert len(session_mgr.sessions) == 2


class TestCleanupIdleSessions:
    """Test idle session cleanup logic"""

    @pytest.mark.asyncio
    async def test_cleanup_idle_sessions(self, session_mgr, mock_container_manager):
        """Should cleanup sessions that exceed idle timeout"""
        # Create session
        container = await session_mgr.get_or_create_session(
            conversation_id="conv-idle",
            api_key="sk-ant-test-key"
        )

        # Manually set last_active to past idle timeout
        container.last_active = datetime.now(timezone.utc) - timedelta(minutes=2)

        # Run cleanup
        await session_mgr.cleanup_idle_sessions()

        # Session should be removed
        assert len(session_mgr.sessions) == 0
        mock_container_manager.stop_container.assert_called_once_with("test-agent-123")

    @pytest.mark.asyncio
    async def test_keep_active_sessions(self, session_mgr, mock_container_manager):
        """Should keep sessions that are still active"""
        # Create session
        await session_mgr.get_or_create_session(
            conversation_id="conv-active",
            api_key="sk-ant-test-key"
        )

        # Run cleanup
        await session_mgr.cleanup_idle_sessions()

        # Session should still exist
        assert len(session_mgr.sessions) == 1
        mock_container_manager.stop_container.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_multiple_sessions_selectively(self, session_mgr, mock_container_manager):
        """Should cleanup only idle sessions, keep active ones"""
        # Create multiple sessions
        c1 = Mock(spec=AgentContainer)
        c1.agent_id = "agent-1"
        c1.last_active = datetime.now(timezone.utc) - timedelta(minutes=2)  # Idle

        c2 = Mock(spec=AgentContainer)
        c2.agent_id = "agent-2"
        c2.last_active = datetime.now(timezone.utc)  # Active

        mock_container_manager.create_agent_container.side_effect = [c1, c2]

        await session_mgr.get_or_create_session("conv-1", "sk-ant-key")
        await session_mgr.get_or_create_session("conv-2", "sk-ant-key")

        # Run cleanup
        await session_mgr.cleanup_idle_sessions()

        # Only one session should remain
        assert len(session_mgr.sessions) == 1
        mock_container_manager.stop_container.assert_called_once_with("agent-1")


class TestCleanupTask:
    """Test background cleanup task"""

    @pytest.mark.asyncio
    async def test_start_cleanup_task(self, session_mgr):
        """Should start background cleanup task"""
        await session_mgr.start_cleanup_task(interval_minutes=1)

        assert session_mgr._cleanup_task is not None
        assert not session_mgr._cleanup_task.done()

        # Cleanup
        await session_mgr.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_stop_cleanup_task(self, session_mgr):
        """Should stop background cleanup task"""
        await session_mgr.start_cleanup_task(interval_minutes=1)
        await session_mgr.stop_cleanup_task()

        assert session_mgr._cleanup_task is None

    @pytest.mark.asyncio
    async def test_prevent_multiple_cleanup_tasks(self, session_mgr):
        """Should not start multiple cleanup tasks"""
        await session_mgr.start_cleanup_task(interval_minutes=1)

        # Try to start again (should warn but not start new task)
        await session_mgr.start_cleanup_task(interval_minutes=1)

        # Still only one task
        assert session_mgr._cleanup_task is not None

        await session_mgr.stop_cleanup_task()


class TestCleanupAllSessions:
    """Test cleanup of all sessions"""

    @pytest.mark.asyncio
    async def test_cleanup_all_sessions(self, session_mgr, mock_container_manager):
        """Should cleanup all active sessions"""
        # Create multiple sessions
        c1 = Mock(spec=AgentContainer)
        c1.agent_id = "agent-1"
        c1.last_active = datetime.now(timezone.utc)

        c2 = Mock(spec=AgentContainer)
        c2.agent_id = "agent-2"
        c2.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container.side_effect = [c1, c2]

        await session_mgr.get_or_create_session("conv-1", "sk-ant-key")
        await session_mgr.get_or_create_session("conv-2", "sk-ant-key")

        # Cleanup all
        await session_mgr.cleanup_all_sessions()

        # All sessions should be removed
        assert len(session_mgr.sessions) == 0
        assert mock_container_manager.stop_container.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_all_handles_errors(self, session_mgr, mock_container_manager):
        """Should continue cleanup even if some fail"""
        # Create session
        await session_mgr.get_or_create_session("conv-1", "sk-ant-key")

        # Make stop_container raise an error
        mock_container_manager.stop_container.side_effect = Exception("Cleanup failed")

        # Should not raise exception
        await session_mgr.cleanup_all_sessions()

        # Sessions should still be cleared
        assert len(session_mgr.sessions) == 0


class TestActiveSessionsCount:
    """Test active sessions count"""

    @pytest.mark.asyncio
    async def test_get_active_sessions_count(self, session_mgr, mock_container_manager):
        """Should return correct count of active sessions"""
        assert session_mgr.get_active_sessions_count() == 0

        await session_mgr.get_or_create_session("conv-1", "sk-ant-key")
        assert session_mgr.get_active_sessions_count() == 1

        # Create different containers for different sessions
        c2 = Mock(spec=AgentContainer)
        c2.agent_id = "agent-2"
        c2.last_active = datetime.now(timezone.utc)
        mock_container_manager.create_agent_container.return_value = c2

        await session_mgr.get_or_create_session("conv-2", "sk-ant-key")
        assert session_mgr.get_active_sessions_count() == 2


class TestCreateSessionFromConfig:
    """Test config-based session creation"""

    @pytest.mark.asyncio
    async def test_create_session_with_config_id(self, session_mgr, mock_container_manager):
        """Should create session from config ID"""
        # Mock container with config metadata
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent-123"
        mock_container.config_id = "code-assistant"
        mock_container.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            return_value=mock_container
        )

        # Mock config loader
        with patch('agcluster.container.core.session_manager.load_config_from_id') as mock_load:
            mock_config = AgentConfig(
                id="code-assistant",
                name="Code Assistant",
                allowed_tools=["Bash", "Read"]
            )
            mock_load.return_value = mock_config

            session_id, container = await session_mgr.create_session_from_config(
                conversation_id="conv-123",
                api_key="sk-ant-test-key",
                config_id="code-assistant"
            )

            assert session_id == "conv-conv-123"
            assert container.agent_id == "test-agent-123"
            assert container.config_id == "code-assistant"
            mock_load.assert_called_once_with("code-assistant")
            mock_container_manager.create_agent_container_from_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_with_inline_config(self, session_mgr, mock_container_manager):
        """Should create session from inline config"""
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent-456"
        mock_container.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            return_value=mock_container
        )

        inline_config = AgentConfig(
            id="custom-agent",
            name="Custom Agent",
            allowed_tools=["Read", "Write"]
        )

        session_id, container = await session_mgr.create_session_from_config(
            conversation_id="conv-456",
            api_key="sk-ant-test-key",
            config=inline_config
        )

        assert session_id == "conv-conv-456"
        assert container.agent_id == "test-agent-456"
        # Should be called with inline config
        call_args = mock_container_manager.create_agent_container_from_config.call_args
        assert call_args[1]['config'] == inline_config

    @pytest.mark.asyncio
    async def test_create_session_without_config_raises_error(self, session_mgr):
        """Should raise ValueError if neither config_id nor config provided"""
        with pytest.raises(ValueError, match="Either config_id or config must be provided"):
            await session_mgr.create_session_from_config(
                conversation_id="conv-789",
                api_key="sk-ant-test-key"
            )

    @pytest.mark.asyncio
    async def test_create_session_replaces_existing(self, session_mgr, mock_container_manager):
        """Should replace existing session with same ID"""
        # First container
        container1 = Mock(spec=AgentContainer)
        container1.agent_id = "agent-1"
        container1.config_id = "config-1"
        container1.last_active = datetime.now(timezone.utc)

        # Second container
        container2 = Mock(spec=AgentContainer)
        container2.agent_id = "agent-2"
        container2.config_id = "config-2"
        container2.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            side_effect=[container1, container2]
        )
        mock_container_manager.stop_container = AsyncMock()

        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        # Create first session
        await session_mgr.create_session_from_config(
            conversation_id="conv-replace",
            api_key="sk-ant-key",
            config=config
        )

        # Create second session with same conversation ID
        session_id, container = await session_mgr.create_session_from_config(
            conversation_id="conv-replace",
            api_key="sk-ant-key",
            config=config
        )

        # Should have stopped first container
        mock_container_manager.stop_container.assert_called_once_with("agent-1")
        # Should have new container
        assert container.agent_id == "agent-2"


class TestGetSession:
    """Test session retrieval"""

    @pytest.mark.asyncio
    async def test_get_existing_session(self, session_mgr, mock_container_manager):
        """Should retrieve existing session"""
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent"
        mock_container.config_id = "code-assistant"
        mock_container.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            return_value=mock_container
        )

        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        # Create session
        session_id, _ = await session_mgr.create_session_from_config(
            conversation_id="conv-get",
            api_key="sk-ant-key",
            config=config
        )

        # Get session
        container = await session_mgr.get_session(session_id)
        assert container.agent_id == "test-agent"
        assert container.config_id == "code-assistant"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_raises_error(self, session_mgr):
        """Should raise SessionNotFoundError for non-existent session"""
        with pytest.raises(SessionNotFoundError, match="Session conv-nonexistent not found"):
            await session_mgr.get_session("conv-nonexistent")

    @pytest.mark.asyncio
    async def test_get_session_updates_last_active(self, session_mgr, mock_container_manager):
        """Should update last_active when getting session"""
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent"
        mock_container.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            return_value=mock_container
        )

        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        session_id, _ = await session_mgr.create_session_from_config(
            conversation_id="conv-active",
            api_key="sk-ant-key",
            config=config
        )

        original_time = mock_container.last_active
        await asyncio.sleep(0.1)

        # Get session should update last_active
        await session_mgr.get_session(session_id)
        assert mock_container.last_active > original_time


class TestListSessions:
    """Test session listing"""

    @pytest.mark.asyncio
    async def test_list_empty_sessions(self, session_mgr):
        """Should return empty dict when no sessions"""
        sessions = session_mgr.list_sessions()
        assert sessions == {}

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_mgr, mock_container_manager):
        """Should list all active sessions with metadata"""
        # Create mock containers
        container1 = Mock(spec=AgentContainer)
        container1.agent_id = "agent-1"
        container1.config_id = "config-1"
        container1.container_ip = "172.18.0.2"
        container1.created_at = datetime.now(timezone.utc)
        container1.last_active = datetime.now(timezone.utc)

        container2 = Mock(spec=AgentContainer)
        container2.agent_id = "agent-2"
        container2.config_id = "config-2"
        container2.container_ip = "172.18.0.3"
        container2.created_at = datetime.now(timezone.utc)
        container2.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            side_effect=[container1, container2]
        )

        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        # Create two sessions
        await session_mgr.create_session_from_config("conv-1", "sk-ant-key", config=config)
        await session_mgr.create_session_from_config("conv-2", "sk-ant-key", config=config)

        # List sessions
        sessions = session_mgr.list_sessions()

        assert len(sessions) == 2
        assert "conv-conv-1" in sessions
        assert "conv-conv-2" in sessions

        # Check metadata
        session1 = sessions["conv-conv-1"]
        assert session1["agent_id"] == "agent-1"
        assert session1["config_id"] == "config-1"
        assert session1["container_ip"] == "172.18.0.2"
        assert "created_at" in session1
        assert "last_active" in session1


class TestCleanupSession:
    """Test single session cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_specific_session(self, session_mgr, mock_container_manager):
        """Should cleanup a specific session"""
        mock_container = Mock(spec=AgentContainer)
        mock_container.agent_id = "test-agent"
        mock_container.last_active = datetime.now(timezone.utc)

        mock_container_manager.create_agent_container_from_config = AsyncMock(
            return_value=mock_container
        )
        mock_container_manager.stop_container = AsyncMock()

        config = AgentConfig(id="test", name="Test", allowed_tools=["Bash"])

        # Create session
        session_id, _ = await session_mgr.create_session_from_config(
            conversation_id="conv-cleanup",
            api_key="sk-ant-key",
            config=config
        )

        # Cleanup session
        await session_mgr.cleanup_session(session_id)

        # Session should be removed
        assert session_id not in session_mgr.sessions
        mock_container_manager.stop_container.assert_called_once_with("test-agent")

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_session(self, session_mgr, mock_container_manager):
        """Should handle cleanup of non-existent session gracefully"""
        mock_container_manager.stop_container = AsyncMock()

        # Should not raise exception
        await session_mgr.cleanup_session("conv-nonexistent")

        # Should not call stop_container
        mock_container_manager.stop_container.assert_not_called()
