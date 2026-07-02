from app.models.recipe import ExtractedRecipe

SYSTEM_PROMPT = (
    "You extract a structured recipe from raw, noisy webpage text scraped from a mako.co.il "
    "recipe page. Identify the recipe name, every ingredient with its amount (if stated), and "
    "the ordered preparation steps. Ignore any leftover navigation, ads, or unrelated site "
    "content. Preserve the original Hebrew wording of the recipe name, ingredients, and "
    "instructions -- do not translate."
)


def build_user_prompt(extracted: ExtractedRecipe) -> str:
    title_line = f"Page title: {extracted.title}\n" if extracted.title else ""
    return (
        f"{title_line}"
        f"Source URL: {extracted.source_url}\n\n"
        f"Raw page text:\n{extracted.raw_text}"
    )
