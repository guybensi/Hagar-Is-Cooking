import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog + stdlib logging to emit structured JSON-ish key=value logs."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event"]),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


def bind_chat_context(chat_id: int) -> None:
    """Bind chat_id to structlog's contextvars so every log line for this update includes it.

    Each incoming Telegram update is processed in its own asyncio Task by python-telegram-bot,
    so contextvars-based binding is naturally isolated per update -- no explicit teardown needed.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(chat_id=chat_id)
