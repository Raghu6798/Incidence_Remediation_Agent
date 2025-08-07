# Configuration Management

This document describes the comprehensive configuration management system for the DevOps Agent using Pydantic BaseSettings with modern validation patterns.

## Overview

The DevOps Agent uses Pydantic BaseSettings for type-safe configuration management with the following features:

- **Type Safety**: All configuration values are validated against their expected types
- **Environment Variable Support**: Automatic loading from environment variables and .env files
- **Modern Validation**: Uses the latest Pydantic validation patterns with `@field_validator` and `@model_validator`
- **Nested Configuration**: Organized into logical sections (logging, LLM, GitHub, agent)
- **Validation**: Comprehensive validation with custom error messages
- **Environment-Specific**: Support for different environments (development, staging, production)

## Quick Start

### Basic Usage

```python
from DevOps_Agent.src.config.settings import get_settings, validate_settings

# Load settings (automatically loads from .env file)
settings = get_settings()

# Validate required settings
validate_settings()

# Access configuration
print(f"Environment: {settings.environment}")
print(f"Log level: {settings.logging.log_level}")
print(f"Available LLM providers: {settings.get_available_llm_providers()}")
```

### Environment File Setup

Create a `.env` file in your project root:

```env
# Environment Configuration
ENVIRONMENT=development
DEBUG=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/devops_agent.log
LOG_CONSOLE=true
LOG_FILE_ENABLED=true
LOG_ROTATION=10 MB
LOG_RETENTION=30 days

# LLM Configuration
GOOGLE_API_KEY=your_google_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_MODEL=gemini-2.5-flash
DEFAULT_TEMPERATURE=0.4

# GitHub Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
GITHUB_API_BASE_URL=https://api.github.com

# Agent Configuration
AGENT_NAME=DevOps Incident Response Agent
AGENT_VERSION=1.0.0
```

## Configuration Structure

### Main Settings Class

The main `Settings` class combines all configuration sections:

```python
class Settings(BaseSettings):
    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
        case_sensitive=False,
    )
    
    # Configuration sections
    logging: LoggingSettings
    llm: LLMSettings
    github: GitHubSettings
    agent: AgentSettings
    
    # Environment settings
    environment: str
    debug: bool
```

### Logging Configuration

```python
class LoggingSettings(BaseSettings):
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default="logs/devops_agent.log")
    log_console: bool = Field(default=True, description="Enable console logging")
    log_file_enabled: bool = Field(default=True, description="Enable file logging")
    log_rotation: str = Field(default="10 MB", description="Log rotation")
    log_retention: str = Field(default="30 days", description="Log retention")
    
    @field_validator('log_level', mode='after')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'log_level must be one of {allowed_levels}')
        return v.upper()
```

### LLM Configuration

```python
class LLMSettings(BaseSettings):
    # API Keys
    google_api_key: Optional[str] = Field(default=None)
    openrouter_api_key: Optional[str] = Field(default=None)
    claude_api_key: Optional[str] = Field(default=None)
    cerebras_api_key: Optional[str] = Field(default=None)
    mistral_api_key: Optional[str] = Field(default=None)
    
    # Model Configuration
    default_model: str = Field(default="gemini-2.5-flash")
    default_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    default_timeout: int = Field(default=30, ge=1)
    
    @field_validator('default_temperature', mode='after')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v
```

## Modern Validation Patterns

### Field Validators

The configuration system uses modern Pydantic validation patterns:

#### After Validators

```python
@field_validator('log_level', mode='after')
@classmethod
def validate_log_level(cls, v: str) -> str:
    """Validate log level is one of the allowed values."""
    allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if v.upper() not in allowed_levels:
        raise ValueError(f'log_level must be one of {allowed_levels}')
    return v.upper()
```

#### Custom Error Messages

```python
from pydantic_core import PydanticCustomError

@field_validator('api_rate_limit', mode='after')
@classmethod
def validate_rate_limit(cls, v: int) -> int:
    """Validate API rate limit is reasonable."""
    if v > 1000:
        raise PydanticCustomError(
            'rate_limit_too_high',
            'Rate limit cannot exceed 1000 requests per minute',
            {'value': v, 'max': 1000}
        )
    return v
```

### Model Validators

Model-level validation for cross-field validation:

```python
@model_validator(mode='after')
def validate_production_settings(self) -> 'EnhancedSettings':
    """Validate production-specific settings."""
    if self.is_production():
        if self.debug:
            raise ValueError('Debug mode cannot be enabled in production')
        
        if self.logging.log_console:
            raise ValueError('Console logging should be disabled in production')
    
    return self
```

## Environment Variable Mapping

### Flat Structure

Environment variables map directly to field names:

```env
LOG_LEVEL=INFO
GOOGLE_API_KEY=your_key_here
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
```

### Nested Structure

Use double underscores for nested configuration:

```env
LOGGING__LOG_LEVEL=DEBUG
LLM__GOOGLE_API_KEY=your_key_here
GITHUB__GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
```

### Field Mapping

| Environment Variable | Setting Path | Description |
|---------------------|--------------|-------------|
| `LOG_LEVEL` | `logging.log_level` | Logging level |
| `LOG_FILE` | `logging.log_file` | Log file path |
| `GOOGLE_API_KEY` | `llm.google_api_key` | Google API key |
| `OPENROUTER_API_KEY` | `llm.openrouter_api_key` | OpenRouter API key |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `github.github_personal_access_token` | GitHub token |
| `ENVIRONMENT` | `environment` | Environment name |
| `DEBUG` | `debug` | Debug mode |

## Configuration Management

### Configuration Manager

The `ConfigurationManager` class provides utilities for managing configurations:

```python
from DevOps_Agent.src.config.config_manager import ConfigurationManager

# Create manager
manager = ConfigurationManager()

# Load settings
settings = manager.load_settings()

# Validate configuration
validation = manager.validate_configuration()
print(f"Valid: {validation['valid']}")
print(f"Errors: {validation['errors']}")
print(f"Warnings: {validation['warnings']}")

# Export configuration
json_config = manager.export_configuration("json")
env_config = manager.export_configuration("env")

# Create environment-specific config
dev_config = manager.create_environment_config("development")
prod_config = manager.create_environment_config("production")
```

### Environment-Specific Templates

The system provides templates for different environments:

#### Development

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_CONSOLE=true
LOG_ROTATION=1 MB
LOG_RETENTION=7 days
DEFAULT_TEMPERATURE=0.7
ENABLE_DEBUG_MODE=true
```

#### Staging

```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
LOG_CONSOLE=false
LOG_ROTATION=50 MB
LOG_RETENTION=30 days
DEFAULT_TEMPERATURE=0.4
ENABLE_DEBUG_MODE=false
```

#### Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_CONSOLE=false
LOG_ROTATION=100 MB
LOG_RETENTION=90 days
DEFAULT_TEMPERATURE=0.3
ENABLE_DEBUG_MODE=false
```

## Validation and Error Handling

### Required Settings Validation

```python
def validate_required_settings(self) -> List[str]:
    """Validate that all required settings are present."""
    missing_settings = []
    
    # Check for at least one LLM API key
    llm_keys = [
        self.llm.google_api_key,
        self.llm.openrouter_api_key,
        self.llm.claude_api_key,
        self.llm.cerebras_api_key,
        self.llm.mistral_api_key
    ]
    
    if not any(key for key in llm_keys if key):
        missing_settings.append("At least one LLM API key is required")
    
    # Check GitHub token
    if not self.github.github_personal_access_token:
        missing_settings.append("GitHub Personal Access Token is required")
    
    return missing_settings
```

### Environment File Validation

```python
from DevOps_Agent.src.config.config_manager import validate_env_file

# Validate .env file
validation = validate_env_file(".env")
print(f"Valid: {validation['valid']}")
print(f"Errors: {validation['errors']}")
print(f"Warnings: {validation['warnings']}")
```

## Advanced Features

### Enhanced Settings

The `EnhancedSettings` class extends the base settings with additional features:

```python
class EnhancedSettings(Settings):
    # Additional fields
    api_rate_limit: int = Field(default=100, ge=1, le=10000)
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=300, ge=1)
    
    # Custom validation
    @field_validator('api_rate_limit', mode='after')
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        if v > 1000:
            raise PydanticCustomError(
                'rate_limit_too_high',
                'Rate limit cannot exceed 1000 requests per minute',
                {'value': v, 'max': 1000}
            )
        return v
    
    # Model validation
    @model_validator(mode='after')
    def validate_production_settings(self) -> 'EnhancedSettings':
        if self.is_production():
            if self.debug:
                raise ValueError('Debug mode cannot be enabled in production')
        return self
```

### Configuration Summary

```python
from DevOps_Agent.src.config.config_manager import create_config_summary

# Generate configuration summary
summary = create_config_summary()
print(summary)
```

## Best Practices

### 1. Environment-Specific Configuration

- Use different `.env` files for different environments
- Never commit sensitive data to version control
- Use environment variables in production

### 2. Validation

- Always validate configuration on startup
- Use appropriate field constraints (ge, le, etc.)
- Provide meaningful error messages

### 3. Security

- Never log sensitive configuration values
- Use placeholder values in example files
- Rotate API keys regularly

### 4. Type Safety

- Use proper type annotations
- Leverage Pydantic's built-in validation
- Use custom validators for complex logic

## Migration from Old System

If you're migrating from the old environment variable system:

1. **Update imports**:
   ```python
   # Old
   import os
   api_key = os.getenv("GOOGLE_API_KEY")
   
   # New
   from DevOps_Agent.src.config.settings import get_settings
   settings = get_settings()
   api_key = settings.llm.google_api_key
   ```

2. **Update validation**:
   ```python
   # Old
   if not os.getenv("GOOGLE_API_KEY"):
       raise ValueError("GOOGLE_API_KEY not found")
   
   # New
   from DevOps_Agent.src.config.settings import validate_settings
   validate_settings()
   ```

3. **Update configuration access**:
   ```python
   # Old
   log_level = os.getenv("LOG_LEVEL", "INFO")
   
   # New
   log_level = settings.logging.log_level
   ```

## Troubleshooting

### Common Issues

1. **Configuration not loading**:
   - Check if `.env` file exists in project root
   - Verify environment variable names match field names
   - Check file permissions

2. **Validation errors**:
   - Review error messages for specific field issues
   - Check field constraints (ge, le, etc.)
   - Verify required fields are set

3. **Type errors**:
   - Ensure environment variables match expected types
   - Check for extra whitespace in .env file
   - Verify boolean values are 'true'/'false' or '1'/'0'

### Debug Mode

Enable debug mode to see detailed validation information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from DevOps_Agent.src.config.settings import get_settings
settings = get_settings()
```

## Examples

### Complete Configuration Example

```python
from DevOps_Agent.src.config.settings import get_settings, validate_settings
from DevOps_Agent.src.config.config_manager import ConfigurationManager

# Load and validate settings
settings = get_settings()
validate_settings()

# Create configuration manager
manager = ConfigurationManager()

# Validate configuration
validation = manager.validate_configuration()
if not validation['valid']:
    print("Configuration errors:")
    for error in validation['errors']:
        print(f"  - {error}")
    exit(1)

# Use configuration
print(f"Environment: {settings.environment}")
print(f"Log level: {settings.logging.log_level}")
print(f"Available LLM providers: {settings.get_available_llm_providers()}")

# Export configuration
config_json = manager.export_configuration("json")
print(f"Configuration: {config_json}")
```

### Environment-Specific Setup

```python
from DevOps_Agent.src.config.config_manager import ConfigurationManager

manager = ConfigurationManager()

# Create environment-specific configurations
environments = ["development", "staging", "production"]

for env in environments:
    config = manager.create_environment_config(
        environment=env,
        output_file=f"config/.env.{env}"
    )
    print(f"Created {env} configuration")
```

This configuration system provides a robust, type-safe, and maintainable way to manage all aspects of the DevOps Agent's configuration while following modern Python and Pydantic best practices. 