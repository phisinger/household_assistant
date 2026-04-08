"""In-memory session manager with TTL expiry."""

from datetime import datetime, timedelta, timezone
from typing import Any
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """In-memory session storage with automatic TTL expiry."""

    def __init__(self, ttl_minutes: int = 15):
        """Initialize with TTL in minutes."""
        self.ttl_minutes = ttl_minutes
        self._sessions: dict[str, dict[str, Any]] = {}
        # _sessions = {
        #     "chat_id": {
        #         "messages": [...],
        #         "updated_at": datetime
        #     }
        # }

    async def initialize(self) -> None:
        """No-op for compatibility."""
        logger.info(f"SessionManager initialized (in-memory, TTL={self.ttl_minutes}min)")

    async def get_messages(self, chat_id: int | str) -> list[dict[str, Any]]:
        """Get messages for a chat, removing expired sessions.

        Args:
            chat_id: Telegram chat ID

        Returns:
            List of message dicts (HumanMessage/AIMessage format)
        """
        chat_id = str(chat_id)

        # Clean up all expired sessions
        await self._cleanup_expired()

        # Return messages or empty list
        if chat_id in self._sessions:
            return self._sessions[chat_id]["messages"]
        return []

    async def save_messages(
        self, chat_id: int | str, messages: list[dict[str, Any]]
    ) -> None:
        """Save messages in memory with update timestamp.

        Args:
            chat_id: Telegram chat ID
            messages: List of message dicts
        """
        chat_id = str(chat_id)
        now = datetime.now(timezone.utc)

        self._sessions[chat_id] = {
            "messages": messages,
            "updated_at": now,
        }

    async def _cleanup_expired(self) -> int:
        """Remove sessions older than TTL.

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.ttl_minutes)
        expired_chats = [
            chat_id
            for chat_id, session in self._sessions.items()
            if session["updated_at"] < cutoff
        ]

        for chat_id in expired_chats:
            del self._sessions[chat_id]
            logger.debug(f"Expired session: {chat_id}")

        return len(expired_chats)

    async def clear_expired(self) -> int:
        """Public method for clearing expired sessions."""
        return await self._cleanup_expired()
