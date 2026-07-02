from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RecipeHistoryORM
from app.models.recipe import FinalRecipe


@dataclass(frozen=True)
class RecipeHistoryRecord:
    recipe_name: str
    source_url: str | None
    final_recipe_json: str
    delivery_mode: str
    completed_at: datetime


def _to_record(row: RecipeHistoryORM) -> RecipeHistoryRecord:
    return RecipeHistoryRecord(
        recipe_name=row.recipe_name,
        source_url=row.source_url,
        final_recipe_json=row.final_recipe_json,
        delivery_mode=row.delivery_mode,
        completed_at=row.completed_at,
    )


class RecipeHistoryRepository:
    """Logs completed recipes. Never leaks SQLAlchemy ORM objects to callers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        telegram_user_id: int,
        final_recipe: FinalRecipe,
        source_url: str | None,
        delivery_mode: str,
    ) -> None:
        row = RecipeHistoryORM(
            telegram_user_id=telegram_user_id,
            recipe_name=final_recipe.recipe_name,
            source_url=source_url,
            final_recipe_json=final_recipe.model_dump_json(),
            delivery_mode=delivery_mode,
            completed_at=datetime.utcnow(),
        )
        self._session.add(row)
        await self._session.commit()

    async def list_for_user(
        self, telegram_user_id: int, limit: int = 20
    ) -> list[RecipeHistoryRecord]:
        result = await self._session.execute(
            select(RecipeHistoryORM)
            .where(RecipeHistoryORM.telegram_user_id == telegram_user_id)
            .order_by(RecipeHistoryORM.completed_at.desc())
            .limit(limit)
        )
        return [_to_record(row) for row in result.scalars().all()]
