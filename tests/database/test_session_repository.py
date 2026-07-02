from app.database.session_repository import SessionRepository
from app.models.search import SearchResult
from app.models.session import SessionData, SessionState


async def test_get_by_chat_id_returns_none_when_absent(session_factory):
    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        session = await repo.get_by_chat_id(999)

    assert session is None


async def test_upsert_then_get_round_trips_nested_data(session_factory):
    session_data = SessionData(
        chat_id=42,
        state=SessionState.AWAITING_RECIPE_SELECTION,
        dish_query="שניצל",
        search_results=[
            SearchResult(title="שניצל קלאסי", url="https://www.mako.co.il/food/a")
        ],
    )

    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        await repo.upsert(session_data)

    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        restored = await repo.get_by_chat_id(42)

    assert restored.dish_query == "שניצל"
    assert restored.state == SessionState.AWAITING_RECIPE_SELECTION
    assert len(restored.search_results) == 1
    assert restored.search_results[0].title == "שניצל קלאסי"


async def test_upsert_overwrites_existing_row_for_same_chat_id(session_factory):
    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        await repo.upsert(SessionData(chat_id=7, state=SessionState.IDLE))
        await repo.upsert(SessionData(chat_id=7, state=SessionState.AWAITING_CHECKLIST))

    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        session = await repo.get_by_chat_id(7)

    assert session.state == SessionState.AWAITING_CHECKLIST


async def test_delete_removes_the_session(session_factory):
    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        await repo.upsert(SessionData(chat_id=8, state=SessionState.IDLE))
        await repo.delete(8)

    async with session_factory() as db_session:
        repo = SessionRepository(db_session)
        session = await repo.get_by_chat_id(8)

    assert session is None
