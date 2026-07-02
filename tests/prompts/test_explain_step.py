from app.models.recipe import FinalRecipe, Ingredient
from app.prompts import explain_step


def test_system_prompt_is_non_empty():
    assert explain_step.SYSTEM_PROMPT.strip()


def test_build_user_prompt_includes_recipe_and_step_text():
    recipe = FinalRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף")],
        instructions=["לשטוף את החזה", "לטגן עד להזהבה"],
    )

    prompt = explain_step.build_user_prompt(recipe, 1)

    assert "שניצל עוף" in prompt
    assert "לטגן עד להזהבה" in prompt
    assert "לשטוף את החזה" not in prompt
