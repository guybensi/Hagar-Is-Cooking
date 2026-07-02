SYSTEM_PROMPT = (
    "You are a helper that turns a Hebrew (or mixed Hebrew/English) free-text request for a "
    "dish into a short, clean search query naming that dish, suitable for a recipe search "
    "engine. Keep it short (2-5 words), keep it in the same language the user used, and do "
    "not add commentary. If the request already names a specific dish, keep it as-is. If it "
    "describes an ingredient or craving, infer a concrete representative dish name."
)


def build_user_prompt(user_text: str) -> str:
    return f'User request: "{user_text}"\n\nReturn the normalized search query.'
