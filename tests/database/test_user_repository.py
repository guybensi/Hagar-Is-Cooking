from app.database.user_repository import UserRepository


async def test_get_or_create_creates_a_new_user(session_factory):
    async with session_factory() as db_session:
        repo = UserRepository(db_session)
        record = await repo.get_or_create(telegram_user_id=100, username="hagar")

    assert record.telegram_user_id == 100
    assert record.username == "hagar"


async def test_get_or_create_returns_existing_user_without_duplicating(session_factory):
    async with session_factory() as db_session:
        repo = UserRepository(db_session)
        await repo.get_or_create(telegram_user_id=100, username="hagar")
        second = await repo.get_or_create(telegram_user_id=100, username="hagar")

    assert second.telegram_user_id == 100


async def test_touch_last_active_updates_timestamp(session_factory):
    async with session_factory() as db_session:
        repo = UserRepository(db_session)
        created = await repo.get_or_create(telegram_user_id=200, username="hagar")
        await repo.touch_last_active(200)
        refreshed = await repo.get_or_create(telegram_user_id=200, username="hagar")

    assert refreshed.last_active >= created.last_active


async def test_touch_last_active_is_a_no_op_for_unknown_user(session_factory):
    async with session_factory() as db_session:
        repo = UserRepository(db_session)
        # Must not raise.
        await repo.touch_last_active(telegram_user_id=999999)
