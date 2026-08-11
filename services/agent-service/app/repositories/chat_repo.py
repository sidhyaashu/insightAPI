"""Repository for ChatMessage DB operations in agent-service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_message(self, session_id: str, user_id: str, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, user_id=user_id, role=role, content=content)
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

    async def get_session_count_today(self, user_id: str) -> int:
        """Count distinct chat sessions for user today (for tier quota)."""
        from datetime import date
        from sqlalchemy import func, cast, Date
        today = date.today()
        result = await self.db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.user_id == user_id)
            .where(func.date(ChatMessage.created_at) == today)
            .where(ChatMessage.role == "user")
        )
        return result.scalar_one() or 0
