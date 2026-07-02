from app.static import labels


def test_all_labels_are_non_empty_strings():
    for name in dir(labels):
        if name.startswith("_"):
            continue
        value = getattr(labels, name)
        if isinstance(value, str):
            assert value.strip(), f"{name} is blank"


def test_search_results_intro_has_count_placeholder():
    rendered = labels.SEARCH_RESULTS_INTRO.format(count=3)
    assert "3" in rendered
