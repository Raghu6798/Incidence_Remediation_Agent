"""
Configuration management utilities for the DevOps Agent.
This module provides utilities for managing different environment configurations
and demonstrates modern Pydantic validation patterns.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from pydantic import ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from .settings import Settings, get_settings, reload_settings


class ConfigurationManager:
    """
    Configuration manager for handling different environment configurations
    and providing utilities for configuration management.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self._settings: Optional[Settings] = None

    def load_settings(self, env_file: Optional[str] = None) -> Settings:
        """
        Load settings from environment file or use default.

        Args:
            env_file: Path to .env file to load

        Returns:
            Settings instance
        """
        if env_file:
            self._settings = reload_settings(env_file)
        else:
            self._settings = get_settings()

        return self._settings

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration and return validation results.

        Returns:
            Dictionary containing validation results
        """
        if not self._settings:
            self._settings = get_settings()

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "available_providers": [],
            "missing_required": [],
        }

        try:
            # Validate required settings
            missing_settings = self._settings.validate_required_settings()
            if missing_settings:
                validation_results["valid"] = False
                validation_results["missing_required"] = missing_settings
                validation_results["errors"].extend(missing_settings)

            # Check available LLM providers
            available_providers = self._settings.get_available_llm_providers()
            validation_results["available_providers"] = available_providers

            if not available_providers:
                validation_results["warnings"].append("No LLM providers configured")

            # Validate log file path
            try:
                log_path = self._settings.get_log_file_path()
                validation_results["log_file"] = str(log_path)
            except Exception as e:
                validation_results["warnings"].append(
                    f"Log file validation failed: {e}"
                )

            # Environment-specific validations
            if self._settings.is_production():
                if self._settings.debug:
                    validation_results["warnings"].append(
                        "Debug mode enabled in production"
                    )

                if self._settings.logging.log_console:
                    validation_results["warnings"].append(
                        "Console logging enabled in production"
                    )

        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Configuration validation failed: {e}")

        return validation_results

    def export_configuration(self, format: str = "json") -> str:
        """
        Export current configuration to specified format.

        Args:
            format: Output format ('json', 'env')

        Returns:
            Configuration as string
        """
        if not self._settings:
            self._settings = get_settings()

        if format.lower() == "json":
            # Export as JSON (excluding sensitive data)
            config_dict = {
                "environment": self._settings.environment,
                "debug": self._settings.debug,
                "logging": {
                    "log_level": self._settings.logging.log_level,
                    "log_file": self._settings.logging.log_file,
                    "log_console": self._settings.logging.log_console,
                    "log_file_enabled": self._settings.logging.log_file_enabled,
                    "log_rotation": self._settings.logging.log_rotation,
                    "log_retention": self._settings.logging.log_retention,
                },
                "llm": {
                    "default_model": self._settings.llm.default_model,
                    "default_temperature": self._settings.llm.default_temperature,
                    "default_max_tokens": self._settings.llm.default_max_tokens,
                    "default_timeout": self._settings.llm.default_timeout,
                    "openrouter_base_url": self._settings.llm.openrouter_base_url,
                    "available_providers": self._settings.get_available_llm_providers(),
                },
                "github": {
                    "github_api_base_url": self._settings.github.github_api_base_url,
                    "github_api_timeout": self._settings.github.github_api_timeout,
                    "github_rate_limit_warning": self._settings.github.github_rate_limit_warning,
                },
                "agent": {
                    "agent_name": self._settings.agent.agent_name,
                    "agent_version": self._settings.agent.agent_version,
                    "max_concurrent_sessions": self._settings.agent.max_concurrent_sessions,
                    "session_timeout": self._settings.agent.session_timeout,
                    "enable_debug_mode": self._settings.agent.enable_debug_mode,
                },
            }
            return json.dumps(config_dict, indent=2)

        elif format.lower() == "env":
            # Export as .env format (excluding sensitive data)
            env_lines = [
                "# DevOps Agent Configuration Export",
                "# Generated configuration (sensitive data excluded)",
                "",
                f"ENVIRONMENT={self._settings.environment}",
                f"DEBUG={str(self._settings.debug).lower()}",
                "",
                "# Logging Configuration",
                f"LOG_LEVEL={self._settings.logging.log_level}",
                f"LOG_FILE={self._settings.logging.log_file}",
                f"LOG_CONSOLE={str(self._settings.logging.log_console).lower()}",
                f"LOG_FILE_ENABLED={str(self._settings.logging.log_file_enabled).lower()}",
                f"LOG_ROTATION={self._settings.logging.log_rotation}",
                f"LOG_RETENTION={self._settings.logging.log_retention}",
                "",
                "# LLM Configuration",
                f"DEFAULT_MODEL={self._settings.llm.default_model}",
                f"DEFAULT_TEMPERATURE={self._settings.llm.default_temperature}",
                f"DEFAULT_MAX_TOKENS={self._settings.llm.default_max_tokens}",
                f"DEFAULT_TIMEOUT={self._settings.llm.default_timeout}",
                f"OPENROUTER_BASE_URL={self._settings.llm.openrouter_base_url}",
                "",
                "# GitHub Configuration",
                f"GITHUB_API_BASE_URL={self._settings.github.github_api_base_url}",
                f"GITHUB_API_TIMEOUT={self._settings.github.github_api_timeout}",
                f"GITHUB_RATE_LIMIT_WARNING={self._settings.github.github_rate_limit_warning}",
                "",
                "# Agent Configuration",
                f"AGENT_NAME={self._settings.agent.agent_name}",
                f"AGENT_VERSION={self._settings.agent.agent_version}",
                f"MAX_CONCURRENT_SESSIONS={self._settings.agent.max_concurrent_sessions}",
                f"SESSION_TIMEOUT={self._settings.agent.session_timeout}",
                f"ENABLE_DEBUG_MODE={str(self._settings.agent.enable_debug_mode).lower()}",
                "",
                "# Note: API keys and tokens are not exported for security reasons",
                "# Please set them manually in your .env file",
            ]
            return "\n".join(env_lines)

        else:
            raise ValueError(f"Unsupported format: {format}")

    def create_environment_config(
        self, environment: str, output_file: Optional[str] = None
    ) -> str:
        """
        Create environment-specific configuration template.

        Args:
            environment: Environment name (development, staging, production)
            output_file: Optional output file path

        Returns:
            Configuration template as string
        """
        templates = {
            "development": {
                "ENVIRONMENT": "development",
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
                "LOG_CONSOLE": "true",
                "LOG_FILE_ENABLED": "true",
                "LOG_ROTATION": "1 MB",
                "LOG_RETENTION": "7 days",
                "DEFAULT_TEMPERATURE": "0.7",
                "ENABLE_DEBUG_MODE": "true",
            },
            "staging": {
                "ENVIRONMENT": "staging",
                "DEBUG": "false",
                "LOG_LEVEL": "INFO",
                "LOG_CONSOLE": "false",
                "LOG_FILE_ENABLED": "true",
                "LOG_ROTATION": "50 MB",
                "LOG_RETENTION": "30 days",
                "DEFAULT_TEMPERATURE": "0.4",
                "ENABLE_DEBUG_MODE": "false",
            },
            "production": {
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "LOG_LEVEL": "WARNING",
                "LOG_CONSOLE": "false",
                "LOG_FILE_ENABLED": "true",
                "LOG_ROTATION": "100 MB",
                "LOG_RETENTION": "90 days",
                "DEFAULT_TEMPERATURE": "0.3",
                "ENABLE_DEBUG_MODE": "false",
            },
        }

        if environment not in templates:
            raise ValueError(f"Unknown environment: {environment}")

        template = templates[environment]

        # Create .env template
        env_lines = [
            f"# DevOps Agent Configuration - {environment.upper()}",
            f"# Generated configuration template",
            "",
            "# Environment Configuration",
            f"ENVIRONMENT={template['ENVIRONMENT']}",
            f"DEBUG={template['DEBUG']}",
            "",
            "# Logging Configuration",
            f"LOG_LEVEL={template['LOG_LEVEL']}",
            f"LOG_FILE=logs/devops_agent_{environment}.log",
            f"LOG_CONSOLE={template['LOG_CONSOLE']}",
            f"LOG_FILE_ENABLED={template['LOG_FILE_ENABLED']}",
            f"LOG_ROTATION={template['LOG_ROTATION']}",
            f"LOG_RETENTION={template['LOG_RETENTION']}",
            "",
            "# LLM Configuration",
            "GOOGLE_API_KEY=your_google_api_key_here",
            "OPENROUTER_API_KEY=your_openrouter_api_key_here",
            "CLAUDE_API_KEY=your_claude_api_key_here",
            "CEREBRAS_API_KEY=your_cerebras_api_key_here",
            "MISTRAL_API_KEY=your_mistral_api_key_here",
            "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1",
            "DEFAULT_MODEL=gemini-2.5-flash",
            f"DEFAULT_TEMPERATURE={template['DEFAULT_TEMPERATURE']}",
            "DEFAULT_MAX_TOKENS=4096",
            "DEFAULT_TIMEOUT=30",
            "",
            "# GitHub Configuration",
            "GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here",
            "GITHUB_API_BASE_URL=https://api.github.com",
            "GITHUB_API_TIMEOUT=30",
            "GITHUB_RATE_LIMIT_WARNING=100",
            "",
            "# Agent Configuration",
            "AGENT_NAME=DevOps Incident Response Agent",
            "AGENT_VERSION=1.0.0",
            "MAX_CONCURRENT_SESSIONS=10",
            "SESSION_TIMEOUT=300",
            f"ENABLE_DEBUG_MODE={template['ENABLE_DEBUG_MODE']}",
            "",
            "# Security Note: Replace placeholder values with actual credentials",
        ]

        config_content = "\n".join(env_lines)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(config_content)

        return config_content


class EnhancedSettings(Settings):
    """
    Enhanced settings class with additional validation and utilities.
    Demonstrates modern Pydantic validation patterns.
    """

    # Additional fields with custom validation
    api_rate_limit: int = Field(
        default=100, ge=1, le=10000, description="API rate limit per minute"
    )

    cache_enabled: bool = Field(
        default=True, description="Enable caching for API responses"
    )

    cache_ttl: int = Field(default=300, ge=1, description="Cache TTL in seconds")

    # Custom field validators using modern patterns
    @field_validator("api_rate_limit", mode="after")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate API rate limit is reasonable."""
        if v > 1000:
            raise PydanticCustomError(
                "rate_limit_too_high",
                "Rate limit cannot exceed 1000 requests per minute",
                {"value": v, "max": 1000},
            )
        return v

    @field_validator("cache_ttl", mode="after")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache TTL is reasonable."""
        if v > 3600:  # 1 hour
            raise ValueError("Cache TTL cannot exceed 1 hour (3600 seconds)")
        return v

    # Model-level validation
    @model_validator(mode="after")
    def validate_production_settings(self) -> "EnhancedSettings":
        """Validate production-specific settings."""
        if self.is_production():
            if self.debug:
                raise ValueError("Debug mode cannot be enabled in production")

            if self.logging.log_console:
                raise ValueError("Console logging should be disabled in production")

            if self.cache_ttl < 60:
                raise ValueError(
                    "Cache TTL should be at least 60 seconds in production"
                )

        return self

    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return {
            "enabled": self.cache_enabled,
            "ttl": self.cache_ttl,
            "max_size": 1000,
        }

    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return {
            "requests_per_minute": self.api_rate_limit,
            "burst_limit": self.api_rate_limit * 2,
            "window_size": 60,
        }


# Utility functions
def validate_env_file(env_file_path: str) -> Dict[str, Any]:
    """
    Validate an environment file without loading sensitive data.

    Args:
        env_file_path: Path to .env file

    Returns:
        Validation results
    """
    results = {"valid": True, "errors": [], "warnings": [], "variables": {}}

    try:
        env_path = Path(env_file_path)
        if not env_path.exists():
            results["valid"] = False
            results["errors"].append(f"Environment file not found: {env_file_path}")
            return results

        with open(env_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse variable assignment
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")

                    results["variables"][key] = value

                    # Check for common issues
                    if key.endswith("_KEY") or key.endswith("_TOKEN"):
                        if value in ["your_key_here", "your_token_here", ""]:
                            results["warnings"].append(
                                f"Line {line_num}: {key} appears to be a placeholder"
                            )

                    if key == "ENVIRONMENT" and value not in [
                        "development",
                        "staging",
                        "production",
                    ]:
                        results["warnings"].append(
                            f"Line {line_num}: Unknown environment '{value}'"
                        )

                    if key == "LOG_LEVEL" and value.upper() not in [
                        "DEBUG",
                        "INFO",
                        "WARNING",
                        "ERROR",
                        "CRITICAL",
                    ]:
                        results["errors"].append(
                            f"Line {line_num}: Invalid log level '{value}'"
                        )

                else:
                    results["warnings"].append(
                        f"Line {line_num}: Invalid format (no '=' found)"
                    )

    except Exception as e:
        results["valid"] = False
        results["errors"].append(f"Error reading environment file: {e}")

    return results


def create_config_summary() -> str:
    """
    Create a summary of the current configuration.

    Returns:
        Configuration summary as string
    """
    try:
        settings = get_settings()
        manager = ConfigurationManager()
        validation = manager.validate_configuration()

        summary_lines = [
            "DevOps Agent Configuration Summary",
            "=" * 40,
            f"Environment: {settings.environment}",
            f"Debug Mode: {settings.debug}",
            f"Valid Configuration: {validation['valid']}",
            "",
            "Logging Configuration:",
            f"  Level: {settings.logging.log_level}",
            f"  File: {settings.logging.log_file}",
            f"  Console: {settings.logging.log_console}",
            f"  File Enabled: {settings.logging.log_file_enabled}",
            "",
            "LLM Configuration:",
            f"  Available Providers: {', '.join(validation['available_providers']) if validation['available_providers'] else 'None'}",
            f"  Default Model: {settings.llm.default_model}",
            f"  Temperature: {settings.llm.default_temperature}",
            "",
            "GitHub Configuration:",
            f"  API Base URL: {settings.github.github_api_base_url}",
            f"  Timeout: {settings.github.github_api_timeout}s",
            "",
            "Agent Configuration:",
            f"  Name: {settings.agent.agent_name}",
            f"  Version: {settings.agent.agent_version}",
            f"  Max Sessions: {settings.agent.max_concurrent_sessions}",
            f"  Session Timeout: {settings.agent.session_timeout}s",
        ]

        if validation["errors"]:
            summary_lines.extend(
                [
                    "",
                    "Configuration Errors:",
                    *[f"  - {error}" for error in validation["errors"]],
                ]
            )

        if validation["warnings"]:
            summary_lines.extend(
                [
                    "",
                    "Configuration Warnings:",
                    *[f"  - {warning}" for warning in validation["warnings"]],
                ]
            )

        return "\n".join(summary_lines)

    except Exception as e:
        return f"Error generating configuration summary: {e}"


if __name__ == "__main__":
    # Example usage
    print("Configuration Manager Demo")
    print("=" * 30)

    # Create configuration manager
    manager = ConfigurationManager()

    # Load and validate settings
    settings = manager.load_settings()
    validation = manager.validate_configuration()

    print(f"Configuration valid: {validation['valid']}")
    print(f"Available providers: {validation['available_providers']}")

    if validation["errors"]:
        print("Errors:")
        for error in validation["errors"]:
            print(f"  - {error}")

    if validation["warnings"]:
        print("Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    # Export configuration
    print("\nConfiguration Export (JSON):")
    print(manager.export_configuration("json"))

    # Create environment config
    print("\nDevelopment Environment Template:")
    print(manager.create_environment_config("development"))
