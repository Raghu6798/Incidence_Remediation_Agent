import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class LLMArchitecture(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    LLAMA = "llama"
    MISTRAL = "mistral"
    QWEN = "qwen"
    CLAUDE = "claude"
    KIMI_K2 = "kimi_k2"
    GLM = "glm"


@dataclass
class ModelConfig:
    """Configuration for LLM models"""

    model_name: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.4
    timeout: int = 30
    retry_attempts: int = 3
    max_completion_tokens: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for model initialization"""
        config = {
            "model": self.model_name,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }
        if self.max_completion_tokens:
            config["max_completion_tokens"] = self.max_completion_tokens
        if self.base_url:
            config["base_url"] = self.base_url
        if self.api_key:
            config["api_key"] = self.api_key
        return config


class LLMProviderError(Exception):
    """Custom exception for LLM provider errors"""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._validate_environment()

    @abstractmethod
    def _get_required_env_vars(self) -> Dict[str, str]:
        """Return mapping of environment variable names to their purpose"""
        pass

    @abstractmethod
    def _create_model(self):
        """Create and return the actual model instance"""
        pass

    @abstractmethod
    def get_provider_type(self) -> LLMArchitecture:
        """Return the provider type"""
        pass

    def _validate_environment(self):
        """Validate that required environment variables are set"""
        logger.debug(
            f"Validating environment for {self.get_provider_type().value} provider"
        )
        required_vars = self._get_required_env_vars()
        missing_vars = []

        for var_name, purpose in required_vars.items():
            if not os.getenv(var_name):
                missing_vars.append(f"{var_name} ({purpose})")
                logger.error(f"Missing environment variable: {var_name} ({purpose})")

        if missing_vars:
            error_msg = (
                f"Missing required environment variables for {self.get_provider_type().value}: "
                f"{', '.join(missing_vars)}"
            )
            logger.critical(error_msg)
            raise LLMProviderError(error_msg)

        logger.info(
            f"Environment validation passed for {self.get_provider_type().value} provider"
        )

    def get_model(self):
        """Get model instance with lazy loading and caching"""
        if self._model is None:
            logger.debug(
                f"Creating new model instance for {self.get_provider_type().value}"
            )
            try:
                self._model = self._create_model()
                logger.success(
                    f"Successfully created model instance for {self.get_provider_type().value}"
                )
            except Exception as e:
                error_msg = (
                    f"Failed to create {self.get_provider_type().value} model: {str(e)}"
                )
                logger.error(error_msg)
                raise LLMProviderError(error_msg)
        else:
            logger.debug(
                f"Using cached model instance for {self.get_provider_type().value}"
            )
        return self._model

    def __str__(self) -> str:
        return f"{self.get_provider_type().value}({self.config.model_name})"
