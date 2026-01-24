"""Logging configuration for ZenFlow."""

import logging
import logging.handlers
from pathlib import Path
from typing import Any


def setup_logger(config: dict[str, Any]) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        config: Configuration dictionary containing logging settings.
                Expected keys:
                - logging.level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                - logging.file: Log file path

    Returns:
        Configured logger instance.

    Raises:
        ValueError: If log level is invalid.
    """
    logging_config = config.get("logging", {})
    log_level = logging_config.get("level", "INFO").upper()
    log_file = logging_config.get("file", "zenflow.log")

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        raise ValueError(
            f"Invalid log level '{log_level}'. Must be one of: {', '.join(valid_levels)}"
        )

    # Create logger
    logger = logging.getLogger("zenflow")
    logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with rotation (max 5MB per file, keep 3 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, log_level))

    # Console handler for errors and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    # Formatter with timestamp, level, module, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    logger.info("Logger initialized with level: %s, file: %s", log_level, log_file)

    return logger


def get_logger() -> logging.Logger:
    """
    Get the application logger instance.

    Returns:
        Logger instance. If not configured, returns a basic logger.
    """
    logger = logging.getLogger("zenflow")
    if not logger.handlers:
        # Return basic logger if not configured
        logging.basicConfig(level=logging.INFO)
    return logger
