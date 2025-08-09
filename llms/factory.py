from .base import LLMProvider, ModelConfig, LLMArchitecture, LLMProviderError
from .providers import GeminiLLM, CerebrasLLM, OpenAILLM, ClaudeLLM, MistralLLM
from typing import Dict, Type, Optional
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class LLMFactory:
    """Factory class for creating LLM providers"""

    _providers: Dict[LLMArchitecture, Type[LLMProvider]] = {
        LLMArchitecture.GEMINI: GeminiLLM,
        LLMArchitecture.LLAMA: CerebrasLLM,
        LLMArchitecture.OPENAI: OpenAILLM,
        LLMArchitecture.CLAUDE: ClaudeLLM,
        LLMArchitecture.MISTRAL: MistralLLM,
    }

    # Default model configurations
    _default_configs: Dict[LLMArchitecture, ModelConfig] = {
        LLMArchitecture.GEMINI: ModelConfig(
            model_name="gemini-2.5-flash",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
        ),
        LLMArchitecture.LLAMA: ModelConfig(
            model_name="llama-4-scout-17b-16e-instruct",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            temperature=0.4,
        ),
        LLMArchitecture.OPENAI: ModelConfig(
            model_name="openai/gpt-4.1-nano",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            temperature=0.7,
        ),
        LLMArchitecture.CLAUDE: ModelConfig(
            model_name="claude-sonnet-4-20250514",
            api_key=os.getenv("CLAUDE_API_KEY"),
            temperature=0.4,
        ),
    }

    @classmethod
    def create_provider(
        self, provider_type: LLMArchitecture, config: Optional[ModelConfig] = None
    ) -> LLMProvider:
        """Create an LLM provider instance"""
        logger.debug(f"Creating LLM provider for type: {provider_type.value}")

        if provider_type not in self._providers:
            available = ", ".join([p.value for p in self._providers.keys()])
            error_msg = (
                f"Unsupported provider: {provider_type.value}. Available: {available}"
            )
            logger.error(error_msg)
            raise LLMProviderError(error_msg)

        if config is None:
            logger.debug(f"Using default configuration for {provider_type.value}")
            config = self._default_configs.get(provider_type)
            if config is None:
                error_msg = f"No default configuration for {provider_type.value}"
                logger.error(error_msg)
                raise LLMProviderError(error_msg)
        else:
            logger.debug(f"Using custom configuration for {provider_type.value}")

        provider_class = self._providers[provider_type]
        logger.info(
            f"Creating {provider_type.value} provider with model: {config.model_name}"
        )

        try:
            provider = provider_class(config)
            logger.success(f"Successfully created {provider_type.value} provider")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {provider_type.value} provider: {e}")
            raise

    @classmethod
    def register_provider(
        cls, provider_type: LLMArchitecture, provider_class: Type[LLMProvider]
    ):
        """Register a new provider type"""
        cls._providers[provider_type] = provider_class

    @classmethod
    def get_available_providers(cls) -> list[LLMArchitecture]:
        """Get list of available provider types"""
        return list(cls._providers.keys())


# Usage example
if __name__ == "__main__":
   
    custom_config = ModelConfig(
        model_name="openai/gpt-5-mini",
        base_url=os.getenv("OPENROUTER_BASE_URL"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0.3,
        max_completion_tokens=4000,
        timeout=60,
    )

    try:
        provider = LLMFactory.create_provider(LLMArchitecture.OPENAI, custom_config)
        model = provider.get_model()
        print(f"Created custom model: {type(model)}")
        print(provider.config)
    except LLMProviderError as e:
        print(f"Error: {e}")
