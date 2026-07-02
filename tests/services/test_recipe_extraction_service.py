import httpx
import pytest
import respx

from app.services.recipe_extraction_service import RecipeExtractionError, RecipeExtractionService

SAMPLE_HTML = """
<html>
<head><title>שניצל עוף קלאסי</title></head>
<body>
<nav>תפריט ניווט</nav>
<header>לוגו האתר</header>
<div class="ad-banner">פרסומת: קנו עכשיו!</div>
<article>
<h1>שניצל עוף קלאסי</h1>
<div class="ingredients">
<p>2 חזות עוף</p>
<p>2 ביצים</p>
</div>
<div class="instructions">
<p>לשטוף את החזה</p>
<p>לטגן עד להזהבה</p>
</div>
</article>
<div class="social-share">שתפו בפייסבוק</div>
<footer>זכויות יוצרים</footer>
</body>
</html>
"""


@pytest.fixture
def service() -> RecipeExtractionService:
    return RecipeExtractionService()


@respx.mock
async def test_extract_recipe_returns_title_and_recipe_text(service):
    url = "https://www.mako.co.il/food/recipe-1"
    respx.get(url).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))

    result = await service.extract_recipe(url)

    assert result.title == "שניצל עוף קלאסי"
    assert "חזות עוף" in result.raw_text
    assert "לטגן עד להזהבה" in result.raw_text
    assert result.source_url == url


@respx.mock
async def test_extract_recipe_strips_navigation_ads_and_social(service):
    url = "https://www.mako.co.il/food/recipe-1"
    respx.get(url).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))

    result = await service.extract_recipe(url)

    assert "תפריט ניווט" not in result.raw_text
    assert "פרסומת" not in result.raw_text
    assert "שתפו בפייסבוק" not in result.raw_text
    assert "זכויות יוצרים" not in result.raw_text


@respx.mock
async def test_extract_recipe_raises_on_http_error(service):
    url = "https://www.mako.co.il/food/missing"
    respx.get(url).mock(return_value=httpx.Response(404))

    with pytest.raises(RecipeExtractionError):
        await service.extract_recipe(url)


@respx.mock
async def test_extract_recipe_caps_raw_text_length(service):
    url = "https://www.mako.co.il/food/long"
    long_html = f"<html><body><article><h1>ארוך</h1>{'מילה ' * 5000}</article></body></html>"
    respx.get(url).mock(return_value=httpx.Response(200, text=long_html))

    result = await service.extract_recipe(url)

    assert len(result.raw_text) <= 6000
