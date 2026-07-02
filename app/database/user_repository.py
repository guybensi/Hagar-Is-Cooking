from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import UserORM


@dataclass(frozen=True)
class UserRecord:
    telegram_user_id: int
    username: str | None
    first_seen: datetime
    last_active: datetime


def _to_record(row: UserORM) -> UserRecord:
    return UserRecord(
        telegram_user_id=row.telegram_user_id,
        username=row.username,
        first_seen=row.first_seen,
        last_active=row.last_active,
    )


class UserRepository:
    """Persists Telegram users. Never leaks SQLAlchemy ORM objects to callers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, telegram_user_id: int, username: str | None) -> UserRecord:
        row = await self._get_row(telegram_user_id)
        if row is not None:
            return _to_record(row)

        now = datetime.utcnow()
        row = UserORM(
            telegram_user_id=telegram_user_id,
            username=username,
            first_seen=now,
            last_active=now,
        )
        self._session.add(row)
        await self._session.commit()
        return _to_record(row)

    async def touch_last_active(self, telegram_user_id: int) -> None:
        row = await self._get_row(telegram_user_id)
        if row is not None:
            row.last_active = datetime.utcnow()
            await self._session.commit()

    async def _get_row(self, telegram_user_id: int) -> UserORM | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()
