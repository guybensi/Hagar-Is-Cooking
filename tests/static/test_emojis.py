from app.static import emojis


def test_all_emoji_constants_are_non_empty_strings():
    for name in dir(emojis):
        if name.startswith("_"):
            continue
        value = getattr(emojis, name)
        assert isinstance(value, str)
        assert value.strip()
