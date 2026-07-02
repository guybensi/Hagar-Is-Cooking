import pytest
from pydantic import ValidationError

from app.models.search import SearchResult


def test_search_result_accepts_valid_url():
    result = SearchResult(title="Schnitzel", url="https://www.mako.co.il/food/recipe-1")
    assert str(result.url) == "https://www.mako.co.il/food/recipe-1"


def test_search_result_rejects_invalid_url():
    with pytest.raises(ValidationError):
        SearchResult(title="Schnitzel", url="not-a-url")


def test_search_result_snippet_defaults_to_none():
    result = SearchResult(title="Schnitzel", url="https://www.mako.co.il/food/recipe-1")
    assert result.snippet is None
