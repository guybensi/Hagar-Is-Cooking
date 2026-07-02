from app.models.recipe import Ingredient, StructuredRecipe
from app.models.substitution import SubstitutionAction, SubstitutionDecision
from app.prompts import rewrite_final_recipe


def test_system_prompt_is_non_empty():
    assert rewrite_final_recipe.SYSTEM_PROMPT.strip()


def test_build_user_prompt_includes_all_sections():
    structured = StructuredRecipe(
        recipe_name="שניצל עוף",
        ingredients=[Ingredient(name="חזה עוף"), Ingredient(name="שורש סלרי")],
        instructions=["לטגן"],
    )
    available = [Ingredient(name="חזה עוף")]
    missing = [Ingredient(name="בזיליקום")]
    accepted = [
        SubstitutionDecision(
            ingredient_name="שורש סלרי",
            action=SubstitutionAction.SUBSTITUTE,
            reason="דומה",
            replacement="שורש פטרוזיליה",
        )
    ]

    prompt = rewrite_final_recipe.build_user_prompt(structured, available, missing, accepted)

    assert "שניצל עוף" in prompt
    assert "חזה עוף" in prompt
    assert "בזיליקום" in prompt
    assert "שורש סלרי -> שורש פטרוזיליה" in prompt


def test_build_user_prompt_handles_empty_missing_and_substitutions():
    structured = StructuredRecipe(
        recipe_name="שניצל עוף", ingredients=[Ingredient(name="חזה עוף")], instructions=["לטגן"]
    )

    available = [Ingredient(name="חזה עוף")]
    prompt = rewrite_final_recipe.build_user_prompt(structured, available, [], [])

    assert "(none)" in prompt
