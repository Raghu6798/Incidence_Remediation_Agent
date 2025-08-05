from .base import LLMProvider, ModelConfig, LLMType, LLMProviderError
from .providers import GeminiLLM, CerebrasLLM, OpenAILLM, ClaudeLLM, MistralLLM
from typing import Dict, Type, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class LLMFactory:
    """Factory class for creating LLM providers"""

    _providers: Dict[LLMType, Type[LLMProvider]] = {
        LLMType.GEMINI: GeminiLLM,
        LLMType.LLAMA: CerebrasLLM,
        LLMType.OPENAI: OpenAILLM,
        LLMType.CLAUDE: ClaudeLLM,
        LLMType.MISTRAL: MistralLLM,
    }

    # Default model configurations
    _default_configs: Dict[LLMType, ModelConfig] = {
        LLMType.GEMINI: ModelConfig(
            model_name="gemini-2.5-flash",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.4,
        ),
        LLMType.LLAMA: ModelConfig(
            model_name="llama-4-scout-17b-16e-instruct",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            temperature=0.4,
        ),
        LLMType.OPENAI: ModelConfig(
            model_name="openai/gpt-4.1-nano",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            temperature=0.7,
        ),
        LLMType.CLAUDE: ModelConfig(
            model_name="claude-sonnet-4-20250514",
            api_key=os.getenv("CLAUDE_API_KEY"),
            temperature=0.4,
        ),
    }

    @classmethod
    def create_provider(
        self, provider_type: LLMType, config: Optional[ModelConfig] = None
    ) -> LLMProvider:
        """Create an LLM provider instance"""
        if provider_type not in self._providers:
            available = ", ".join([p.value for p in self._providers.keys()])
            raise LLMProviderError(
                f"Unsupported provider: {provider_type.value}. Available: {available}"
            )

        if config is None:
            config = self._default_configs.get(provider_type)
            if config is None:
                raise LLMProviderError(
                    f"No default configuration for {provider_type.value}"
                )

        provider_class = self._providers[provider_type]
        return provider_class(config)

    @classmethod
    def register_provider(
        cls, provider_type: LLMType, provider_class: Type[LLMProvider]
    ):
        """Register a new provider type"""
        cls._providers[provider_type] = provider_class

    @classmethod
    def get_available_providers(cls) -> list[LLMType]:
        """Get list of available provider types"""
        return list(cls._providers.keys())


# Usage example
if __name__ == "__main__":
    # Basic usage with defaults
    try:
        provider = LLMFactory.create_provider(LLMType.GEMINI)
        model = provider.get_model()
        print(f"Created model: {provider}")
    except LLMProviderError as e:
        print(f"Error: {e}")

    custom_config = ModelConfig(
        model_name="openai/gpt-4.1-nano",
        base_url=os.getenv("OPENROUTER_BASE_URL"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0.3,
        max_tokens=2000,
        timeout=60,
    )

    try:
        provider = LLMFactory.create_provider(LLMType.OPENAI, custom_config)
        model = provider.get_model()
        print(f"Created custom model: {provider}")
    except LLMProviderError as e:
        print(f"Error: {e}")
