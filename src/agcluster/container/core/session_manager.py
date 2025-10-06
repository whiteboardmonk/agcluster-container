"""Session manager for conversation-based container lifecycle"""

import asyncio
import logging
import hashlib
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta

from agcluster.container.core.container_manager import container_manager, AgentContainer

logger = logging.getLogger(__name__)


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
        Generate a unique session ID

        Args:
            conversation_id: Conversation ID from LibreChat (if available)
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

    async def get_or_create_session(
        self,
        conversation_id: Optional[str],
        api_key: str,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[str] = None
    ) -> AgentContainer:
        """
        Get existing session or create new one

        Args:
            conversation_id: Conversation ID from LibreChat
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
            logger.info(f"Reusing existing session {session_id} for agent {agent_container.agent_id}")
            return agent_container

        # Create new session
        logger.info(f"Creating new session {session_id}")
        agent_container = await container_manager.create_agent_container(
            api_key=api_key,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools
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
