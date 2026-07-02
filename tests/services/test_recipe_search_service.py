from unittest.mock import MagicMock

import pytest
import requests

from app.services.recipe_search_service import RecipeSearchError, RecipeSearchService


@pytest.fixture
def service() -> RecipeSearchService:
    svc = RecipeSearchService(api_key="test-key")
    svc._client = MagicMock()
    return svc


async def test_search_recipes_maps_tavily_results_to_search_results(service):
    service._client.search.return_value = {
        "results": [
            {"title": "שניצל קלאסי", "url": "https://www.mako.co.il/food/a", "content": "..."},
            {"title": "שניצל בתנור", "url": "https://www.mako.co.il/food/b", "content": "..."},
        ]
    }

    results = await service.search_recipes("שניצל")

    assert len(results) == 2
    assert results[0].title == "שניצל קלאסי"
    assert "mako.co.il" in str(results[0].url)


async def test_search_recipes_uses_site_restricted_query(service):
    service._client.search.return_value = {"results": []}

    await service.search_recipes("שניצל")

    _, kwargs = service._client.search.call_args
    assert kwargs["query"] == "site:mako.co.il שניצל"


async def test_search_recipes_filters_out_off_domain_results(service):
    service._client.search.return_value = {
        "results": [
            {"title": "On-domain", "url": "https://www.mako.co.il/food/a", "content": "..."},
            {"title": "Off-domain", "url": "https://www.example.com/recipe", "content": "..."},
        ]
    }

    results = await service.search_recipes("שניצל")

    assert len(results) == 1
    assert results[0].title == "On-domain"


async def test_search_recipes_caps_to_three_results(service):
    service._client.search.return_value = {
        "results": [
            {"title": f"Recipe {i}", "url": f"https://www.mako.co.il/food/{i}", "content": "..."}
            for i in range(5)
        ]
    }

    results = await service.search_recipes("שניצל")

    assert len(results) == 3


async def test_search_recipes_raises_recipe_search_error_on_client_failure(service):
    service._client.search.side_effect = RuntimeError("Tavily is down")

    with pytest.raises(RecipeSearchError):
        await service.search_recipes("שניצל")


async def test_search_recipes_retries_on_transient_connection_error_then_succeeds(service):
    service._client.search.side_effect = [
        requests.exceptions.ConnectionError("network blip"),
        {"results": [{"title": "שניצל", "url": "https://www.mako.co.il/food/a", "content": ""}]},
    ]

    results = await service.search_recipes("שניצל")

    assert len(results) == 1
    assert service._client.search.call_count == 2


async def test_search_recipes_retries_on_timeout_error_then_gives_up(service):
    service._client.search.side_effect = TimeoutError("timed out")

    with pytest.raises(RecipeSearchError):
        await service.search_recipes("שניצל")

    assert service._client.search.call_count == 3
