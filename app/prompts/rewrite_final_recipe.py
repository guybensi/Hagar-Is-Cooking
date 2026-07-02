from app.models.recipe import Ingredient, StructuredRecipe
from app.models.substitution import SubstitutionDecision

SYSTEM_PROMPT = (
    "You rewrite a recipe so its ingredient list and instructions match EXACTLY what the home "
    "cook actually has available. You will be given the original recipe, the ingredients they "
    "have on hand, the ingredients they don't have, and any accepted substitutions. Produce a "
    "final ingredient list using only the available ingredients and the accepted substitute "
    "ingredients -- never an ingredient that is missing and was not substituted. Rewrite the "
    "preparation steps so they are fully consistent with the final ingredient list. Also "
    "include a short list of practical cooking tips. Keep everything in Hebrew, matching the "
    "tone and terminology of the original recipe."
)


def _format_ingredients(ingredients: list[Ingredient]) -> str:
    lines = [f"- {i.name}" + (f" ({i.amount})" if i.amount else "") for i in ingredients]
    return "\n".join(lines) if lines else "(none)"


def build_user_prompt(
    structured: StructuredRecipe,
    available: list[Ingredient],
    missing: list[Ingredient],
    accepted_substitutions: list[SubstitutionDecision],
) -> str:
    original_instructions = "\n".join(
        f"{idx + 1}. {step}" for idx, step in enumerate(structured.instructions)
    )
    substitutions_block = (
        "\n".join(f"- {d.ingredient_name} -> {d.replacement}" for d in accepted_substitutions)
        or "(none)"
    )

    return (
        f"Original recipe: {structured.recipe_name}\n\n"
        f"Original instructions:\n{original_instructions}\n\n"
        f"Ingredients available at home:\n{_format_ingredients(available)}\n\n"
        f"Ingredients NOT available (and not substituted):\n{_format_ingredients(missing)}\n\n"
        f"Accepted substitutions:\n{substitutions_block}"
    )
