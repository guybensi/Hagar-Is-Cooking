from typing import Any

from app.database.session_repository import SessionRepository
from app.models.session import SessionData, SessionState


class SessionService:
    """Owns FSM transition semantics on top of the durable SessionRepository.

    Handlers should go through this service (never mutate SessionData.state directly and
    call the repository themselves) so transition/persistence stays in one place.
    """

    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    async def load_or_create(self, chat_id: int) -> SessionData:
        session = await self._repository.get_by_chat_id(chat_id)
        if session is None:
            session = SessionData(chat_id=chat_id)
            await self._repository.upsert(session)
        return session

    async def start_new_flow(self, chat_id: int, dish_query: str) -> SessionData:
        session = SessionData(
            chat_id=chat_id, dish_query=dish_query, state=SessionState.SEARCHING
        )
        await self._repository.upsert(session)
        return session

    async def advance_to(
        self, session: SessionData, state: SessionState, **updates: Any
    ) -> SessionData:
        session.state = state
        for key, value in updates.items():
            setattr(session, key, value)
        await self._repository.upsert(session)
        return session

    async def reset(self, chat_id: int) -> SessionData:
        session = SessionData(chat_id=chat_id, state=SessionState.IDLE)
        await self._repository.upsert(session)
        return session
