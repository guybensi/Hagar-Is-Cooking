from unittest.mock import patch

import pytest

from app.services.recipe_extraction_service import RecipeExtractionError, RecipeExtractionService

SAMPLE_RESPONSE = {
    "results": [
        {
            "url": "https://www.mako.co.il/food/recipe-1",
            "title": "שניצל עוף קלאסי",
            "raw_content": "שניצל עוף קלאסי\n2 חזות עוף\n2 ביצים\nלשטוף את החזה\nלטגן עד להזהבה",
            "images": [],
        }
    ],
    "failed_results": [],
    "response_time": 0.02,
}


@pytest.fixture
def service() -> RecipeExtractionService:
    return RecipeExtractionService(api_key="test-key")


async def test_extract_recipe_returns_title_and_recipe_text(service):
    url = "https://www.mako.co.il/food/recipe-1"
    with patch.object(service._client, "extract", return_value=SAMPLE_RESPONSE):
        result = await service.extract_recipe(url)

    assert result.title == "שניצל עוף קלאסי"
    assert "חזות עוף" in result.raw_text
    assert "לטגן עד להזהבה" in result.raw_text
    assert result.source_url == url


async def test_extract_recipe_raises_on_failed_result(service):
    url = "https://www.mako.co.il/food/missing"
    response = {
        "results": [],
        "failed_results": [{"url": url, "error": "fetch failed"}],
    }
    with patch.object(service._client, "extract", return_value=response):
        with pytest.raises(RecipeExtractionError):
            await service.extract_recipe(url)


async def test_extract_recipe_raises_on_exception(service):
    url = "https://www.mako.co.il/food/error"
    with patch.object(service._client, "extract", side_effect=Exception("network error")):
        with pytest.raises(RecipeExtractionError):
            await service.extract_recipe(url)


async def test_extract_recipe_caps_raw_text_length(service):
    url = "https://www.mako.co.il/food/long"
    response = {
        "results": [{"url": url, "title": "ארוך", "raw_content": "מילה " * 5000, "images": []}],
        "failed_results": [],
    }
    with patch.object(service._client, "extract", return_value=response):
        result = await service.extract_recipe(url)

    assert len(result.raw_text) <= 6000
