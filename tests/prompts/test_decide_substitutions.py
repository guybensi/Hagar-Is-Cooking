from app.models.recipe import Ingredient, StructuredRecipe
from app.prompts import decide_substitutions


def test_system_prompt_is_non_empty():
    assert decide_substitutions.SYSTEM_PROMPT.strip()


def test_build_user_prompt_includes_recipe_and_missing_ingredients():
    recipe = StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף", amount="500 גרם"), Ingredient(name="שורש סלרי")],
        instructions=["לטגן"],
    )
    missing = [Ingredient(name="שורש סלרי")]

    prompt = decide_substitutions.build_user_prompt(missing, recipe)

    assert "שניצל עוף" in prompt
    assert "חזה עוף" in prompt
    assert "שורש סלרי" in prompt
