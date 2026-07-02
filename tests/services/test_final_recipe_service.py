from unittest.mock import AsyncMock

import pytest

from app.models.recipe import FinalRecipe, Ingredient, StructuredRecipe
from app.services.final_recipe_service import FinalRecipeGenerationError, FinalRecipeService
from app.services.llm.groq_client import LLMStructuringError


@pytest.fixture
def structured() -> StructuredRecipe:
    return StructuredRecipe(
        recipe_name="שניצל עוף", ingredients=[Ingredient(name="חזה עוף")], instructions=["לטגן"]
    )


async def test_generate_returns_final_recipe_on_success(structured):
    groq_client = AsyncMock()
    groq_client.rewrite_final_recipe.return_value = FinalRecipe(
        recipe_name="שניצל עוף מותאם",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לטגן"],
        cooking_tips=["לטגן בשמן חם"],
    )
    service = FinalRecipeService(groq_client)

    result = await service.generate(structured, [Ingredient(name="חזה עוף")], [], [])

    assert result.recipe_name == "שניצל עוף מותאם"
    groq_client.rewrite_final_recipe.assert_awaited_once_with(
        structured, [Ingredient(name="חזה עוף")], [], []
    )


async def test_generate_wraps_llm_structuring_error(structured):
    groq_client = AsyncMock()
    groq_client.rewrite_final_recipe.side_effect = LLMStructuringError("boom")
    service = FinalRecipeService(groq_client)

    with pytest.raises(FinalRecipeGenerationError):
        await service.generate(structured, [], [], [])
