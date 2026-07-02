from unittest.mock import AsyncMock

import pytest

from app.models.recipe import FinalRecipe, Ingredient
from app.services.explanation_service import ExplanationError, ExplanationService
from app.services.llm.groq_client import LLMStructuringError


@pytest.fixture
def recipe() -> FinalRecipe:
    return FinalRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לטגן בשמן חם"],
    )


async def test_explain_returns_explanation_text(recipe):
    groq_client = AsyncMock()
    groq_client.explain_step.return_value = "שמן חם מונע ספיגת שמן מיותרת בבשר."
    service = ExplanationService(groq_client)

    result = await service.explain(recipe, 0)

    assert result == "שמן חם מונע ספיגת שמן מיותרת בבשר."
    groq_client.explain_step.assert_awaited_once_with(recipe, 0)


async def test_explain_wraps_llm_structuring_error(recipe):
    groq_client = AsyncMock()
    groq_client.explain_step.side_effect = LLMStructuringError("boom")
    service = ExplanationService(groq_client)

    with pytest.raises(ExplanationError):
        await service.explain(recipe, 0)
