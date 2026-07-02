def truncate(text: str, max_length: int = 60) -> str:
    """Truncate text for use in Telegram inline keyboard button labels."""
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
