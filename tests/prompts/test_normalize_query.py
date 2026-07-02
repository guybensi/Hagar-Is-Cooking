from app.prompts import normalize_query


def test_system_prompt_is_non_empty():
    assert normalize_query.SYSTEM_PROMPT.strip()


def test_build_user_prompt_includes_user_text():
    prompt = normalize_query.build_user_prompt("בא לי משהו עם עוף")
    assert "בא לי משהו עם עוף" in prompt
