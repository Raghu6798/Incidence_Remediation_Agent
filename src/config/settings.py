import os
from pathlib import Path
from typing import Optional, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    # Log level configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Log file configuration
    log_file: Optional[str] = Field(
        default="logs/devops_agent.log", description="Path to log file"
    )

    # Console logging
    log_console: bool = Field(default=True, description="Enable console logging")

    # File logging
    log_file_enabled: bool = Field(default=True, description="Enable file logging")

    # Log rotation and retention
    log_rotation: str = Field(
        default="10 MB",
        description="Log rotation size or time (e.g., '10 MB', '1 day', '00:00')",
    )

    log_retention: str = Field(
        default="30 days",
        description="Log retention period (e.g., '30 days', '1 week')",
    )

    @field_validator("log_level", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}")
        return v.upper()


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    # API Keys
    google_api_key: Optional[str] = Field(
        default=None, description="Google API key for Gemini models"
    )

    openrouter_api_key: Optional[str] = Field(
        default=None, description="OpenRouter API key for OpenAI models"
    )

    claude_api_key: Optional[str] = Field(default=None, description="Claude API key")

    cerebras_api_key: Optional[str] = Field(
        default=None, description="Cerebras API key for Llama models"
    )

    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")

    # OpenRouter configuration
    openrouter_base_url: Optional[str] = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter base URL"
    )

    default_model: str = Field(
        default="gemini-2.5-flash", description="Default model to use"
    )

    default_temperature: float = Field(
        default=0.4,
        ge=0.0,
        le=2.0,
        description="Default temperature for model inference",
    )

    default_max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=8192,
        description="Default maximum tokens for model inference",
    )

    default_timeout: int = Field(
        default=30, ge=1, description="Default timeout for API calls in seconds"
    )

    @field_validator("default_temperature", mode="after")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is within valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v


class GitHubSettings(BaseSettings):
    """GitHub configuration settings."""

    github_personal_access_token: Optional[str] = Field(
        default=None, description="GitHub Personal Access Token"
    )

    github_api_base_url: str = Field(
        default="https://api.github.com", description="GitHub API base URL"
    )

    github_api_timeout: int = Field(
        default=30, ge=1, description="GitHub API timeout in seconds"
    )

    github_rate_limit_warning: int = Field(
        default=100, ge=1, description="GitHub API rate limit warning threshold"
    )


class AgentSettings(BaseSettings):
    """Agent-specific configuration settings."""

    agent_name: str = Field(
        default="DevOps Incident Response Agent", description="Name of the agent"
    )

    agent_version: str = Field(default="1.0.0", description="Agent version")

    max_concurrent_sessions: int = Field(
        default=10, ge=1, description="Maximum number of concurrent sessions"
    )

    session_timeout: int = Field(
        default=300, ge=60, description="Session timeout in seconds"
    )

    enable_debug_mode: bool = Field(
        default=False, description="Enable debug mode for development"
    )


class Settings(BaseSettings):
    """
    Main settings class that combines all configuration sections.

    This class uses Pydantic BaseSettings to automatically load configuration
    from environment variables and .env files with type validation.
    """

    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",  # Ignore extra fields in .env file
        case_sensitive=False,  # Allow case-insensitive environment variables
    )

    # Configuration sections
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging configuration"
    )

    llm: LLMSettings = Field(
        default_factory=LLMSettings, description="LLM configuration"
    )

    github: GitHubSettings = Field(
        default_factory=GitHubSettings, description="GitHub configuration"
    )

    agent: AgentSettings = Field(
        default_factory=AgentSettings, description="Agent configuration"
    )

    # Environment and deployment settings
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    debug: bool = Field(default=False, description="Enable debug mode")

    # Validation methods
    @field_validator("environment", mode="after")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed_envs = ["development", "staging", "production"]
        if v.lower() not in allowed_envs:
            raise ValueError(f"environment must be one of {allowed_envs}")
        return v.lower()

    def validate_required_settings(self) -> List[str]:
        """
        Validate that all required settings are present.

        Returns:
            List of missing required settings
        """
        missing_settings = []

        # Check for at least one LLM API key
        llm_keys = [
            self.llm.google_api_key,
            self.llm.openrouter_api_key,
            self.llm.claude_api_key,
            self.llm.cerebras_api_key,
            self.llm.mistral_api_key,
        ]

        if not any(key for key in llm_keys if key):
            missing_settings.append("At least one LLM API key is required")

        # Check GitHub token
        if not self.github.github_personal_access_token:
            missing_settings.append("GitHub Personal Access Token is required")

        return missing_settings

    def get_available_llm_providers(self) -> List[str]:
        """
        Get list of available LLM providers based on configured API keys.

        Returns:
            List of available provider names
        """
        providers = []

        if self.llm.google_api_key:
            providers.append("gemini")

        if self.llm.openrouter_api_key:
            providers.append("openai")

        if self.llm.claude_api_key:
            providers.append("claude")

        if self.llm.cerebras_api_key:
            providers.append("llama")

        if self.llm.mistral_api_key:
            providers.append("mistral")

        return providers

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    def get_log_file_path(self) -> Path:
        """Get the log file path, creating directories if needed."""
        log_path = Path(self.logging.log_file or "logs/devops_agent.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance, creating it if it doesn't exist.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """
    Reload settings from environment variables and .env file.

    Args:
        env_file: Optional path to .env file to load

    Returns:
        New Settings instance
    """
    global _settings

    if env_file:
        _settings = Settings(_env_file=env_file)
    else:
        _settings = Settings()

    return _settings


def validate_settings() -> None:
    """
    Validate all required settings are present.

    Raises:
        ValueError: If required settings are missing
    """
    settings = get_settings()
    missing_settings = settings.validate_required_settings()

    if missing_settings:
        raise ValueError(f"Missing required settings: {', '.join(missing_settings)}")


# Convenience functions for accessing common settings
def get_logging_config() -> LoggingSettings:
    """Get logging configuration."""
    return get_settings().logging


def get_llm_config() -> LLMSettings:
    """Get LLM configuration."""
    return get_settings().llm


def get_github_config() -> GitHubSettings:
    """Get GitHub configuration."""
    return get_settings().github


def get_agent_config() -> AgentSettings:
    """Get agent configuration."""
    return get_settings().agent


# Environment variable mapping for backward compatibility
def get_env_var_mapping() -> dict:
    """
    Get mapping of settings to environment variables for backward compatibility.

    Returns:
        Dictionary mapping setting names to environment variable names
    """
    return {
        # Logging
        "LOG_LEVEL": "logging.log_level",
        "LOG_FILE": "logging.log_file",
        "LOG_CONSOLE": "logging.log_console",
        "LOG_FILE_ENABLED": "logging.log_file_enabled",
        "LOG_ROTATION": "logging.log_rotation",
        "LOG_RETENTION": "logging.log_retention",
        # LLM
        "GOOGLE_API_KEY": "llm.google_api_key",
        "OPENROUTER_API_KEY": "llm.openrouter_api_key",
        "CLAUDE_API_KEY": "llm.claude_api_key",
        "CEREBRAS_API_KEY": "llm.cerebras_api_key",
        "MISTRAL_API_KEY": "llm.mistral_api_key",
        "OPENROUTER_BASE_URL": "llm.openrouter_base_url",
        # GitHub
        "GITHUB_PERSONAL_ACCESS_TOKEN": "github.github_personal_access_token",
        "GITHUB_API_BASE_URL": "github.github_api_base_url",
        # Agent
        "ENVIRONMENT": "environment",
        "DEBUG": "debug",
    }


if __name__ == "__main__":
    # Example usage and validation
    try:
        settings = get_settings()
        print("✅ Settings loaded successfully")
        print(f"Environment: {settings.environment}")
        print(f"Available LLM providers: {settings.get_available_llm_providers()}")
        print(f"Log file: {settings.get_log_file_path()}")

        # Validate settings
        validate_settings()
        print("✅ All required settings are present")

    except Exception as e:
        print(f"❌ Settings validation failed: {e}")
        exit(1)