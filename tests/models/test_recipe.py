from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.recipe import ExtractedRecipe, FinalRecipe, Ingredient, StructuredRecipe


def test_structured_recipe_requires_at_least_one_ingredient_and_instruction():
    with pytest.raises(ValidationError):
        StructuredRecipe(recipe_name="Schnitzel", ingredients=[], instructions=["Fry it"])

    with pytest.raises(ValidationError):
        StructuredRecipe(
            recipe_name="Schnitzel", ingredients=[Ingredient(name="Chicken")], instructions=[]
        )


def test_structured_recipe_accepts_valid_data():
    recipe = StructuredRecipe(
        recipe_name="Schnitzel",
        ingredients=[Ingredient(name="Chicken breast", amount="500g")],
        instructions=["Bread the chicken", "Fry until golden"],
    )
    assert recipe.recipe_name == "Schnitzel"
    assert recipe.ingredients[0].amount == "500g"


def test_final_recipe_cooking_tips_default_to_empty_list():
    recipe = FinalRecipe(
        recipe_name="Schnitzel",
        ingredients=[Ingredient(name="Chicken breast")],
        instructions=["Fry it"],
    )
    assert recipe.cooking_tips == []


def test_extracted_recipe_requires_fetched_at():
    recipe = ExtractedRecipe(
        source_url="https://www.mako.co.il/food/recipe-1",
        title="Schnitzel",
        raw_text="...",
        fetched_at=datetime.utcnow(),
    )
    assert recipe.title == "Schnitzel"
