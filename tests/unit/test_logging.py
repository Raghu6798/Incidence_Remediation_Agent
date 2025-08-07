"""
Unit tests for the logging configuration module.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_config import setup_logging, get_logger, setup_logging_from_env


class TestLoggingConfig:
    """Test cases for logging configuration."""

    def setup_method(self):
        """Setup method for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
        )

        logger = get_logger("test")
        logger.info("Test message")

        # Check if log file was created
        assert self.log_file.exists()

        # Check if message was written
        with open(self.log_file, "r") as f:
            content = f.read()
            assert "Test message" in content
            assert "INFO" in content

    def test_setup_logging_console_only(self):
        """Test console-only logging."""
        with patch("sys.stdout") as mock_stdout:
            setup_logging(log_level="INFO", enable_console=True, enable_file=False)

            logger = get_logger("test")
            logger.info("Console test message")

            # Check if message was written to stdout
            mock_stdout.write.assert_called()

    def test_setup_logging_custom_format(self):
        """Test custom log format."""
        custom_format = "<level>{level}</level> | {message}"

        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
            format_string=custom_format,
        )

        logger = get_logger("test")
        logger.info("Custom format test")

        with open(self.log_file, "r") as f:
            content = f.read()
            assert "INFO" in content
            assert "Custom format test" in content

    def test_get_logger_with_name(self):
        """Test getting logger with specific name."""
        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
        )

        logger = get_logger("test_module")
        logger.info("Named logger test")

        with open(self.log_file, "r") as f:
            content = f.read()
            assert "test_module" in content

    def test_log_levels(self):
        """Test different log levels."""
        setup_logging(
            log_level="DEBUG",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
        )

        logger = get_logger("test")

        # Test all log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        logger.success("Success message")

        with open(self.log_file, "r") as f:
            content = f.read()
            assert "DEBUG" in content
            assert "INFO" in content
            assert "WARNING" in content
            assert "ERROR" in content
            assert "CRITICAL" in content
            assert "SUCCESS" in content

    def test_setup_logging_from_env(self):
        """Test environment-based logging setup."""
        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FILE": str(self.log_file),
            "LOG_CONSOLE": "false",
            "LOG_FILE_ENABLED": "true",
            "LOG_ROTATION": "1 MB",
            "LOG_RETENTION": "7 days",
        }

        with patch.dict(os.environ, env_vars):
            setup_logging_from_env()

            logger = get_logger("test")
            logger.debug("Environment test message")

            assert self.log_file.exists()

            with open(self.log_file, "r") as f:
                content = f.read()
                assert "DEBUG" in content
                assert "Environment test message" in content

    def test_log_rotation(self):
        """Test log rotation functionality."""
        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
            rotation="1 KB",  # Small size for testing
        )

        logger = get_logger("test")

        # Write enough data to trigger rotation
        large_message = "x" * 1000
        for i in range(10):
            logger.info(f"Large message {i}: {large_message}")

        # Check if rotation files were created
        log_dir = self.log_file.parent
        log_files = list(log_dir.glob(f"{self.log_file.stem}.*"))
        assert len(log_files) > 0

    def test_exception_logging(self):
        """Test exception logging with tracebacks."""
        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
        )

        logger = get_logger("test")

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.exception("Exception occurred")

        with open(self.log_file, "r") as f:
            content = f.read()
            assert "Exception occurred" in content
            assert "ValueError: Test exception" in content
            assert "Traceback" in content

    def test_thread_safety(self):
        """Test thread-safe logging."""
        import threading
        import time

        setup_logging(
            log_level="INFO",
            log_file=str(self.log_file),
            enable_console=False,
            enable_file=True,
        )

        logger = get_logger("test")

        def worker(thread_id):
            for i in range(10):
                logger.info(f"Thread {thread_id} message {i}")
                time.sleep(0.01)

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Check if all messages were logged
        with open(self.log_file, "r") as f:
            content = f.read()
            for i in range(5):
                assert f"Thread {i} message" in content


if __name__ == "__main__":
    pytest.main([__file__])
