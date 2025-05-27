import logging

from rich.logging import RichHandler

from app.core.config import config

#logging_config.py
LOGGING_LEVEL = config.LOGGING_LEVEL


def setup_logging():
    """
    Set up the logging configuration.
    """
    logging.basicConfig(
        level=LOGGING_LEVEL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                markup=True,
                show_path=True,
                keywords=RichHandler.KEYWORDS
                + [
                    "task_id",
                    "assistant_id",
                    "thread_id",
                    "run_id",
                    "file_id",
                    "message_id",
                ],  # Add your custom keywords
            )
        ],
    )

    # Optionally, set higher logging levels for verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


# Initialize logging when this module is imported
setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: The name of the logger.

    Returns:
        A logger instance.
    """
    return logging.getLogger(name) 