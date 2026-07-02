from datetime import datetime

from sqlalchemy import inspect, select

from app.database.engine import session_scope
from app.database.models import SessionORM, UserORM


async def test_init_db_creates_all_tables(db_engine):
    async with db_engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

    assert {"users", "sessions", "recipe_history"} <= set(table_names)


async def test_session_scope_round_trips_a_row(session_factory):
    now = datetime.utcnow()

    async with session_scope(session_factory) as session:
        session.add(
            UserORM(telegram_user_id=42, username="hagar", first_seen=now, last_active=now)
        )
        await session.commit()

    async with session_scope(session_factory) as session:
        result = await session.execute(select(UserORM).where(UserORM.telegram_user_id == 42))
        user = result.scalar_one()

    assert user.username == "hagar"


async def test_session_orm_stores_json_blob(session_factory):
    now = datetime.utcnow()

    async with session_scope(session_factory) as session:
        session.add(
            SessionORM(
                chat_id=123,
                state="IDLE",
                session_data='{"chat_id": 123, "state": "IDLE"}',
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    async with session_scope(session_factory) as session:
        result = await session.execute(select(SessionORM).where(SessionORM.chat_id == 123))
        row = result.scalar_one()

    assert row.state == "IDLE"
    assert "IDLE" in row.session_data
