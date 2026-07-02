from datetime import datetime

from app.models.recipe import ExtractedRecipe
from app.prompts import structure_recipe


def test_system_prompt_is_non_empty():
    assert structure_recipe.SYSTEM_PROMPT.strip()


def test_build_user_prompt_includes_source_url_title_and_raw_text():
    extracted = ExtractedRecipe(
        source_url="https://www.mako.co.il/food/a",
        title="שניצל",
        raw_text="מרכיבים...",
        fetched_at=datetime.utcnow(),
    )

    prompt = structure_recipe.build_user_prompt(extracted)

    assert "https://www.mako.co.il/food/a" in prompt
    assert "מרכיבים" in prompt
    assert "שניצל" in prompt
