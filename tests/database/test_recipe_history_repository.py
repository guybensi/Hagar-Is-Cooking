from datetime import datetime, timedelta

from app.database.models import RecipeHistoryORM
from app.database.recipe_history_repository import RecipeHistoryRepository
from app.models.recipe import FinalRecipe, Ingredient


def _final_recipe() -> FinalRecipe:
    return FinalRecipe(
        recipe_name="שניצל עוף מותאם",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לטגן"],
    )


async def test_add_then_list_for_user_returns_the_record(session_factory):
    async with session_factory() as db_session:
        repo = RecipeHistoryRepository(db_session)
        await repo.add(100, _final_recipe(), "https://www.mako.co.il/food/a", "full")

    async with session_factory() as db_session:
        repo = RecipeHistoryRepository(db_session)
        records = await repo.list_for_user(100)

    assert len(records) == 1
    assert records[0].recipe_name == "שניצל עוף מותאם"
    assert records[0].delivery_mode == "full"
    assert records[0].source_url == "https://www.mako.co.il/food/a"


async def test_list_for_user_only_returns_that_users_recipes(session_factory):
    async with session_factory() as db_session:
        repo = RecipeHistoryRepository(db_session)
        await repo.add(100, _final_recipe(), None, "full")
        await repo.add(200, _final_recipe(), None, "interactive")

    async with session_factory() as db_session:
        records = await RecipeHistoryRepository(db_session).list_for_user(100)

    assert len(records) == 1


async def test_list_for_user_returns_empty_list_when_no_history(session_factory):
    async with session_factory() as db_session:
        records = await RecipeHistoryRepository(db_session).list_for_user(999)

    assert records == []


async def test_list_for_user_orders_most_recent_first(session_factory):
    # Insert rows directly with explicit, well-separated timestamps -- relying on two real
    # datetime.utcnow() calls to differ is flaky on coarse-resolution clocks.
    now = datetime.utcnow()
    async with session_factory() as db_session:
        db_session.add(
            RecipeHistoryORM(
                telegram_user_id=100,
                recipe_name="שניצל עוף מותאם",
                source_url=None,
                final_recipe_json=_final_recipe().model_dump_json(),
                delivery_mode="full",
                completed_at=now,
            )
        )
        db_session.add(
            RecipeHistoryORM(
                telegram_user_id=100,
                recipe_name="פסטה ברוטב עגבניות",
                source_url=None,
                final_recipe_json=_final_recipe().model_dump_json(),
                delivery_mode="interactive",
                completed_at=now + timedelta(minutes=5),
            )
        )
        await db_session.commit()

    async with session_factory() as db_session:
        records = await RecipeHistoryRepository(db_session).list_for_user(100)

    assert records[0].recipe_name == "פסטה ברוטב עגבניות"
