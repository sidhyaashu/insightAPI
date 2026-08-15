"""Repository for ChatSession and ChatMessage DB operations in agent-service."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── ChatSession CRUD ──────────────────────────────────────────────────────

    async def create_session(self, user_id: str, title: str = "New Conversation") -> ChatSession:
        """Create a new DB-persisted chat session and return it."""
        session = ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str, user_id: str) -> ChatSession | None:
        """Fetch a single session, verifying user ownership."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.is_archived == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[ChatSession]:
        """Return all active sessions for a user, most recently updated first."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.is_archived == False)  # noqa: E712
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_session_title(self, session_id: str, user_id: str, title: str) -> bool:
        """Update session title (also bumps updated_at via onupdate)."""
        result = await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .values(title=title, updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def archive_session(self, session_id: str, user_id: str) -> bool:
        """Soft-delete: mark session as archived."""
        result = await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .values(is_archived=True, updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def touch_session(self, session_id: str) -> None:
        """Bump updated_at on message send so list stays sorted correctly."""
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    # ── ChatMessage ops ───────────────────────────────────────────────────────

    async def save_message(
        self, session_id: str, user_id: str, role: str, content: str
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id, user_id=user_id, role=role, content=content
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_history(self, session_id: str, limit: int = 50) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_message_count(self, session_id: str) -> int:
        result = await self.db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        return result.scalar_one() or 0

    async def get_session_count_today(self, user_id: str) -> int:
        """Count distinct chat sessions for user today (for tier quota)."""
        from datetime import date
        from sqlalchemy import cast, Date

        today = date.today()
        result = await self.db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.user_id == user_id)
            .where(func.date(ChatMessage.created_at) == today)
            .where(ChatMessage.role == "user")
        )
        return result.scalar_one() or 0
