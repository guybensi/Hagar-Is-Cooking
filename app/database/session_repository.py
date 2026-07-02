from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SessionORM
from app.models.session import SessionData


class SessionRepository:
    """Persists the full in-progress flow (SessionData) as a JSON blob keyed by chat_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_chat_id(self, chat_id: int) -> SessionData | None:
        row = await self._get_row(chat_id)
        if row is None:
            return None
        return SessionData.model_validate_json(row.session_data)

    async def upsert(self, session_data: SessionData) -> None:
        row = await self._get_row(session_data.chat_id)
        now = datetime.utcnow()
        session_data.updated_at = now

        if row is None:
            row = SessionORM(
                chat_id=session_data.chat_id,
                state=session_data.state,
                session_data=session_data.model_dump_json(),
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.state = session_data.state
            row.session_data = session_data.model_dump_json()
            row.updated_at = now

        await self._session.commit()

    async def delete(self, chat_id: int) -> None:
        row = await self._get_row(chat_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.commit()

    async def _get_row(self, chat_id: int) -> SessionORM | None:
        result = await self._session.execute(
            select(SessionORM).where(SessionORM.chat_id == chat_id)
        )
        return result.scalar_one_or_none()
