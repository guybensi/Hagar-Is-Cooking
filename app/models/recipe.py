from datetime import datetime

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str
    amount: str | None = None


class ExtractedRecipe(BaseModel):
    source_url: str
    title: str | None = None
    raw_text: str
    fetched_at: datetime


class StructuredRecipe(BaseModel):
    recipe_name: str
    ingredients: list[Ingredient] = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)


class FinalRecipe(BaseModel):
    recipe_name: str
    ingredients: list[Ingredient]
    instructions: list[str]
    cooking_tips: list[str] = Field(default_factory=list)
