from unittest.mock import AsyncMock

import pytest

from app.models.recipe import Ingredient, StructuredRecipe
from app.models.substitution import SubstitutionAction, SubstitutionDecision
from app.services.llm.groq_client import LLMStructuringError
from app.services.substitution_service import SubstitutionDecisionError, SubstitutionService


@pytest.fixture
def recipe() -> StructuredRecipe:
    return StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף"), Ingredient(name="שורש סלרי")],
        instructions=["לטגן"],
    )


async def test_decide_returns_decisions_on_success(recipe):
    groq_client = AsyncMock()
    groq_client.decide_substitutions.return_value = [
        SubstitutionDecision(
            ingredient_name="שורש סלרי",
            action=SubstitutionAction.SUBSTITUTE,
            reason="דומה בטעם",
            replacement="שורש פטרוזיליה",
        )
    ]
    service = SubstitutionService(groq_client)

    decisions = await service.decide([Ingredient(name="שורש סלרי")], recipe)

    assert len(decisions) == 1
    assert decisions[0].action == SubstitutionAction.SUBSTITUTE


async def test_decide_wraps_llm_structuring_error(recipe):
    groq_client = AsyncMock()
    groq_client.decide_substitutions.side_effect = LLMStructuringError("boom")
    service = SubstitutionService(groq_client)

    with pytest.raises(SubstitutionDecisionError):
        await service.decide([Ingredient(name="שורש סלרי")], recipe)
