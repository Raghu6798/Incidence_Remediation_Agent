import os
import sys
from pathlib import Path
from loguru import logger
from typing import Optional

from src.config.settings import get_settings, get_logging_config


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    rotation: str = "10 MB",
    retention: str = "30 days",
    format_string: Optional[str] = None,
) -> None:
    """
    Setup loguru logging configuration for the DevOps agent.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (defaults to logs/devops_agent.log)
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        rotation: Log rotation size or time (e.g., "10 MB", "1 day", "00:00")
        retention: Log retention period (e.g., "30 days", "1 week")
        format_string: Custom format string for logs
    """

    # Remove default logger
    logger.remove()

    # Default format if not provided
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Console logging
    if enable_console:
        logger.add(
            sys.stdout,
            format=format_string,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # File logging
    if enable_file:
        if log_file is None:
            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            log_file = logs_dir / "devops_agent.log"

        logger.add(
            str(log_file),
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe logging
        )

    logger.info(f"Logging initialized with level: {log_level}")
    if enable_file:
        logger.info(f"Log file: {log_file}")


def get_logger(name: str = None):
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually __name__ )

    Returns:
        Logger instance
    """
    return logger.bind(name=name) if name else logger


# Environment-based logging setup
def setup_logging_from_env():
    """
    Setup logging based on Pydantic settings configuration.

    This function uses the centralized settings management to configure logging
    with support for .env files and environment variables.
    """
    try:
        # Get logging configuration from Pydantic settings
        logging_config = get_logging_config()

        setup_logging(
            log_level=logging_config.log_level,
            log_file=logging_config.log_file,
            enable_console=logging_config.log_console,
            enable_file=logging_config.log_file_enabled,
            rotation=logging_config.log_rotation,
            retention=logging_config.log_retention,
        )

        logger.info("Logging configured using Pydantic settings")

    except Exception as e:
        # Fallback to environment variables if settings fail to load
        logger.warning(
            f"Failed to load settings, falling back to environment variables: {e}"
        )

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_file = os.getenv("LOG_FILE")
        enable_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        enable_file = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
        rotation = os.getenv("LOG_ROTATION", "10 MB")
        retention = os.getenv("LOG_RETENTION", "30 days")

        setup_logging(
            log_level=log_level,
            log_file=log_file,
            enable_console=enable_console,
            enable_file=enable_file,
            rotation=rotation,
            retention=retention,
        )
