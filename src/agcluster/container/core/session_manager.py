"""Session manager for conversation-based container lifecycle"""

import asyncio
import logging
import hashlib
import secrets
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta

from agcluster.container.core.container_manager import container_manager, AgentContainer
from agcluster.container.core.config_loader import load_config_from_id
from agcluster.container.models.agent_config import AgentConfig

logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Raised when a session is not found"""

    pass


class SessionManager:
    """Manages conversation sessions and container lifecycle"""

    def __init__(self, idle_timeout_minutes: int = 30):
        """
        Initialize session manager

        Args:
            idle_timeout_minutes: Minutes of inactivity before cleaning up a session
        """
        self.sessions: Dict[str, AgentContainer] = {}
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None

    def _generate_session_id(self, conversation_id: Optional[str], api_key: str) -> str:
        """
        Generate a unique session ID (legacy method for backward compatibility)

        Args:
            conversation_id: External conversation ID (if available)
            api_key: User's API key

        Returns:
            Session ID string
        """
        if conversation_id:
            # Use conversation ID directly if provided
            return f"conv-{conversation_id}"

        # Fallback: hash API key to create user-specific session
        # This gives each API key a default session
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
        return f"user-{api_key_hash}"

    async def create_session_from_config(
        self,
        conversation_id: str,
        api_key: str,
        config_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        provider: Optional[str] = None,
    ) -> tuple[str, AgentContainer]:
        """
        Create a new session from configuration

        Args:
            conversation_id: Conversation ID
            api_key: Anthropic API key
            config_id: Optional config ID to load
            config: Optional inline config
            provider: Optional provider name (docker, fly_machines, cloudflare, vercel)

        Returns:
            tuple: (session_id, AgentContainer)

        Raises:
            ValueError: If neither config_id nor config provided
        """
        # Load config if ID provided
        if config_id:
            logger.info(f"Loading config {config_id}")
            config = load_config_from_id(config_id)
            effective_config_id = config_id
        elif config:
            # Inline config - generate secure ID
            effective_config_id = f"inline-{secrets.token_urlsafe(8)}"
            logger.info(f"Using inline config with ID {effective_config_id}")
        else:
            raise ValueError("Either config_id or config must be provided")

        # Generate cryptographically secure session ID
        # Use provided conversation_id if available, otherwise generate secure random ID
        if conversation_id:
            session_id = f"conv-{conversation_id}"
        else:
            session_id = f"conv-{secrets.token_urlsafe(32)}"

        # Check if session already exists
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists, will be replaced")
            await self.cleanup_session(session_id)

        # Use provider-specific container manager if provider specified
        if provider:
            from agcluster.container.core.container_manager import ContainerManager

            logger.info(f"Creating session {session_id} with provider {provider}")
            provider_manager = ContainerManager(provider_name=provider)
            agent_container = await provider_manager.create_agent_container_from_config(
                api_key=api_key, config=config, config_id=effective_config_id
            )
        else:
            # Use global container manager (default provider)
            logger.info(f"Creating session {session_id} with config {effective_config_id}")
            agent_container = await container_manager.create_agent_container_from_config(
                api_key=api_key, config=config, config_id=effective_config_id
            )

        # Store session
        self.sessions[session_id] = agent_container
        logger.info(f"Session {session_id} created with agent {agent_container.agent_id}")

        return session_id, agent_container

    async def get_session(self, session_id: str) -> AgentContainer:
        """
        Get existing session by ID

        Args:
            session_id: Session ID

        Returns:
            AgentContainer for this session

        Raises:
            SessionNotFoundError: If session not found
        """
        if session_id not in self.sessions:
            raise SessionNotFoundError(f"Session {session_id} not found")

        agent_container = self.sessions[session_id]
        # Update last active timestamp
        agent_container.last_active = datetime.now(timezone.utc)
        logger.info(f"Retrieved session {session_id} for agent {agent_container.agent_id}")

        return agent_container

    def list_sessions(self) -> Dict[str, Dict]:
        """
        List all active sessions with metadata

        Returns:
            Dict mapping session_id to session info
        """
        sessions_info = {}
        for session_id, agent_container in self.sessions.items():
            sessions_info[session_id] = {
                "session_id": session_id,
                "agent_id": agent_container.agent_id,
                "config_id": agent_container.config_id,
                "created_at": agent_container.created_at.isoformat(),
                "last_active": agent_container.last_active.isoformat(),
                "container_ip": agent_container.container_ip,
            }
        return sessions_info

    async def cleanup_session(self, session_id: str):
        """
        Cleanup a specific session

        Args:
            session_id: Session ID to cleanup
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found for cleanup")
            return

        agent_container = self.sessions[session_id]
        try:
            await container_manager.stop_container(agent_container.agent_id)
            del self.sessions[session_id]
            logger.info(f"Cleaned up session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")

    async def get_or_create_session(
        self,
        conversation_id: Optional[str],
        api_key: str,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[str] = None,
    ) -> AgentContainer:
        """
        Get existing session or create new one (legacy method)

        Note: This method is maintained for backward compatibility.
        New code should use create_session_from_config()

        Args:
            conversation_id: External conversation ID
            api_key: Anthropic API key
            system_prompt: Optional system prompt
            allowed_tools: Optional allowed tools

        Returns:
            AgentContainer for this session
        """
        session_id = self._generate_session_id(conversation_id, api_key)

        # Check if session already exists
        if session_id in self.sessions:
            agent_container = self.sessions[session_id]
            # Update last active timestamp
            agent_container.last_active = datetime.now(timezone.utc)
            logger.info(
                f"Reusing existing session {session_id} for agent {agent_container.agent_id}"
            )
            return agent_container

        # Create new session
        logger.info(f"Creating new session {session_id} (legacy mode)")
        agent_container = await container_manager.create_agent_container(
            api_key=api_key, system_prompt=system_prompt, allowed_tools=allowed_tools
        )

        # Store session
        self.sessions[session_id] = agent_container
        logger.info(f"Session {session_id} created with agent {agent_container.agent_id}")

        return agent_container

    async def cleanup_idle_sessions(self):
        """Remove sessions that have been idle for longer than timeout"""
        now = datetime.now(timezone.utc)
        sessions_to_remove = []

        for session_id, agent_container in self.sessions.items():
            idle_time = now - agent_container.last_active

            if idle_time > self.idle_timeout:
                sessions_to_remove.append((session_id, agent_container))
                logger.info(
                    f"Session {session_id} idle for {idle_time.total_seconds()/60:.1f} minutes "
                    f"(agent {agent_container.agent_id})"
                )

        # Cleanup idle sessions
        for session_id, agent_container in sessions_to_remove:
            try:
                await container_manager.stop_container(agent_container.agent_id)
                del self.sessions[session_id]
                logger.info(f"Cleaned up idle session {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} idle sessions")

    async def start_cleanup_task(self, interval_minutes: int = 5):
        """
        Start background task to cleanup idle sessions

        Args:
            interval_minutes: How often to check for idle sessions
        """
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    await self.cleanup_idle_sessions()
                except asyncio.CancelledError:
                    logger.info("Cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}", exc_info=True)

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started session cleanup task (interval: {interval_minutes} minutes)")

    async def stop_cleanup_task(self):
        """Stop the background cleanup task"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped session cleanup task")

    async def cleanup_all_sessions(self):
        """Cleanup all active sessions (called on shutdown)"""
        logger.info(f"Cleaning up all {len(self.sessions)} active sessions")

        for session_id, agent_container in list(self.sessions.items()):
            try:
                await container_manager.stop_container(agent_container.agent_id)
                logger.info(f"Cleaned up session {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")

        self.sessions.clear()

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)


# Global session manager instance
session_manager = SessionManager(idle_timeout_minutes=30)
