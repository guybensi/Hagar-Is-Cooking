from app.database.session_repository import SessionRepository
from app.models.session import SessionState
from app.services.session_service import SessionService


async def test_load_or_create_creates_a_fresh_idle_session(session_factory):
    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        session = await service.load_or_create(chat_id=1)

    assert session.chat_id == 1
    assert session.state == SessionState.IDLE


async def test_load_or_create_returns_existing_session(session_factory):
    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        await service.start_new_flow(chat_id=1, dish_query="פסטה")

    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        session = await service.load_or_create(chat_id=1)

    assert session.dish_query == "פסטה"
    assert session.state == SessionState.SEARCHING


async def test_advance_to_updates_state_and_arbitrary_fields(session_factory):
    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        session = await service.load_or_create(chat_id=2)
        updated = await service.advance_to(
            session, SessionState.AWAITING_RECIPE_SELECTION, dish_query="שניצל"
        )

    assert updated.state == SessionState.AWAITING_RECIPE_SELECTION
    assert updated.dish_query == "שניצל"


async def test_reset_returns_session_to_idle(session_factory):
    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        session = await service.load_or_create(chat_id=3)
        await service.advance_to(session, SessionState.AWAITING_CHECKLIST)

    async with session_factory() as db_session:
        service = SessionService(SessionRepository(db_session))
        reset_session = await service.reset(chat_id=3)

    assert reset_session.state == SessionState.IDLE
