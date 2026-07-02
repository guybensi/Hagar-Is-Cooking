from app.utils.text import truncate


def test_truncate_leaves_short_text_unchanged():
    assert truncate("שניצל", 60) == "שניצל"


def test_truncate_shortens_long_text_with_ellipsis():
    long_title = "א" * 100
    result = truncate(long_title, max_length=10)

    assert len(result) == 10
    assert result.endswith("…")


def test_truncate_strips_whitespace():
    assert truncate("  שניצל  ", 60) == "שניצל"
