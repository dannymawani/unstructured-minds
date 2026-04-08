"""Tests for logging configuration."""

import logging

from src.logging_config import (
    configure_logging,
    get_logger,
)


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_debug(self):
        """Test logging configuration in debug mode."""
        configure_logging(debug=True, json_logs=False)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_production(self):
        """Test logging configuration in production mode."""
        configure_logging(debug=False, json_logs=True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_custom_level(self):
        """Test logging configuration with custom level."""
        configure_logging(log_level="WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_has_handler(self):
        """Test that root logger has at least one handler."""
        configure_logging(debug=True)
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self):
        """Test getting a logger with a name."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_without_name(self):
        """Test getting a logger without a name."""
        logger = get_logger()
        assert logger is not None


class TestSpecializedLoggers:
    """Tests for specialized logger getters via get_logger(name)."""

    def test_get_api_logger(self):
        """Test getting API logger."""
        logger = get_logger("api")
        assert logger is not None

    def test_get_db_logger(self):
        """Test getting database logger."""
        logger = get_logger("db")
        assert logger is not None

    def test_get_extraction_logger(self):
        """Test getting extraction logger."""
        logger = get_logger("extraction")
        assert logger is not None
