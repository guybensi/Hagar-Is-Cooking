from app.utils.logging import configure_logging, get_logger


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
