from app.models.recipe import Ingredient, StructuredRecipe

SYSTEM_PROMPT = (
    "You help a home cook who is missing some ingredients for a recipe. For EACH missing "
    "ingredient listed, decide exactly one action: BUY (it's essential with no good substitute "
    "-- the user should go buy it), SKIP (it's optional or minor and can be left out), or "
    "SUBSTITUTE (propose a common, easy-to-find replacement with a very similar culinary role). "
    "Always give a short one-sentence reason in Hebrew. When the action is SUBSTITUTE, always "
    "include a concrete replacement ingredient name in Hebrew."
)


def build_user_prompt(missing_ingredients: list[Ingredient], recipe: StructuredRecipe) -> str:
    ingredients_block = "\n".join(
        f"- {i.name}" + (f" ({i.amount})" if i.amount else "") for i in recipe.ingredients
    )
    missing_block = "\n".join(
        f"- {i.name}" + (f" ({i.amount})" if i.amount else "") for i in missing_ingredients
    )
    return (
        f"Recipe: {recipe.recipe_name}\n\n"
        f"Full ingredient list:\n{ingredients_block}\n\n"
        f"Missing ingredients (decide BUY/SKIP/SUBSTITUTE for each of these):\n{missing_block}"
    )
