import structlog

from app.utils.logging import bind_chat_context, configure_logging, get_logger


def test_configure_logging_does_not_raise():
    configure_logging("DEBUG")
    configure_logging("INFO")


def test_get_logger_returns_usable_logger():
    configure_logging("INFO")
    logger = get_logger("test")

    assert logger is not None
    assert hasattr(logger, "info")
    # Should not raise even with structured kwargs.
    logger.info("test_event", foo="bar")


def test_bind_chat_context_adds_chat_id_to_contextvars():
    bind_chat_context(42)

    assert structlog.contextvars.get_contextvars()["chat_id"] == 42


def test_bind_chat_context_clears_previous_context():
    bind_chat_context(1)
    structlog.contextvars.bind_contextvars(extra_field="should_be_cleared")

    bind_chat_context(2)

    context = structlog.contextvars.get_contextvars()
    assert context["chat_id"] == 2
    assert "extra_field" not in context
