from app.models.recipe import FinalRecipe

SYSTEM_PROMPT = (
    "You explain, in very simple Hebrew, WHY one specific cooking step in a recipe matters. "
    "Maximum two short sentences. No preamble, and don't just repeat the step itself -- give "
    "the underlying reason, in plain language a beginner cook would understand."
)


def build_user_prompt(recipe: FinalRecipe, step_index: int) -> str:
    step_text = recipe.instructions[step_index]
    return (
        f"Recipe: {recipe.recipe_name}\n\n"
        f"Step: {step_text}\n\n"
        "Explain briefly why this step matters."
    )
