#!/usr/bin/env python3
"""
Demo script showing loguru-based logging functionality for the DevOps Agent.
This script demonstrates different logging levels, file rotation, and error handling.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_config import setup_logging, get_logger


def demo_basic_logging():
    """Demonstrate basic logging functionality."""
    logger = get_logger(__name__)

    logger.info("Starting basic logging demo")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    logger.success("This is a success message")


def demo_error_logging():
    """Demonstrate error logging with tracebacks."""
    logger = get_logger("error_demo")

    logger.info("Demonstrating error logging")

    try:
        # Simulate an error
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.error(f"Caught division by zero error: {e}")
        logger.exception("Full traceback for the error:")

    try:
        # Simulate another error
        undefined_variable = some_undefined_variable
    except NameError as e:
        logger.error(f"Caught name error: {e}")
        logger.exception("Full traceback for the name error:")


def demo_structured_logging():
    """Demonstrate structured logging with context."""
    logger = get_logger("structured_demo")

    # Log with additional context
    user_id = "user123"
    action = "login"
    ip_address = "192.168.1.100"

    logger.info(f"User {user_id} performed {action} from {ip_address}")

    # Log with structured data
    event_data = {
        "user_id": user_id,
        "action": action,
        "ip_address": ip_address,
        "timestamp": "2024-01-15T10:30:00Z",
        "status": "success",
    }

    logger.info(f"Event logged: {event_data}")


def demo_performance_logging():
    """Demonstrate performance logging."""
    import time

    logger = get_logger("performance_demo")

    logger.info("Starting performance demo")

    # Simulate a slow operation
    start_time = time.time()
    logger.debug("Starting slow operation")

    time.sleep(2)  # Simulate work

    end_time = time.time()
    duration = end_time - start_time

    logger.info(f"Slow operation completed in {duration:.2f} seconds")

    if duration > 1.5:
        logger.warning(f"Operation took longer than expected: {duration:.2f}s")
    else:
        logger.success(f"Operation completed within expected time: {duration:.2f}s")


def demo_environment_based_logging():
    """Demonstrate environment-based logging configuration."""
    logger = get_logger("env_demo")

    logger.info("Demonstrating environment-based logging")

    # Show current environment variables
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "logs/devops_agent.log")
    enable_console = os.getenv("LOG_CONSOLE", "true")
    enable_file = os.getenv("LOG_FILE_ENABLED", "true")

    logger.info(f"Current logging configuration:")
    logger.info(f"  - Log level: {log_level}")
    logger.info(f"  - Log file: {log_file}")
    logger.info(f"  - Console logging: {enable_console}")
    logger.info(f"  - File logging: {enable_file}")


def main():
    """Main function to run all logging demos."""
    print("=" * 60)
    print("DevOps Agent - Logging Demo")
    print("=" * 60)

    # Setup logging with custom configuration for demo
    setup_logging(
        log_level="DEBUG",
        log_file="logs/demo.log",
        enable_console=True,
        enable_file=True,
        rotation="1 MB",
        retention="7 days",
    )

    logger = get_logger("main")
    logger.info("Starting logging demo session")

    try:
        # Run all demos
        demo_basic_logging()
        print("\n" + "-" * 40)

        demo_error_logging()
        print("\n" + "-" * 40)

        demo_structured_logging()
        print("\n" + "-" * 40)

        demo_performance_logging()
        print("\n" + "-" * 40)

        demo_environment_based_logging()
        print("\n" + "-" * 40)

        logger.success("All logging demos completed successfully!")

    except Exception as e:
        logger.critical(f"Demo failed with error: {e}")
        logger.exception("Full traceback:")
        return 1

    print("\n" + "=" * 60)
    print("Demo completed! Check the logs/demo.log file for detailed logs.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
