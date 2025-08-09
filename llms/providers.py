from .base import LLMProvider, ModelConfig, LLMArchitecture, LLMProviderError
from typing import Dict
import os


class GeminiLLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"GOOGLE_API_KEY": "Google API key for Gemini"}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.GEMINI

    def _create_model(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise LLMProviderError(
                "langchain_google_genai not installed. Run: pip install langchain-google-genai"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("GOOGLE_API_KEY")

        return ChatGoogleGenerativeAI(**model_config)


class CerebrasLLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"CEREBRAS_API_KEY": "Cerebras API key"}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.LLAMA

    def _create_model(self):
        try:
            from langchain_cerebras import ChatCerebras
        except ImportError:
            raise LLMProviderError(
                "langchain_cerebras not installed. Run: pip install langchain-cerebras"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("CEREBRAS_API_KEY")

        return ChatCerebras(**model_config)


class QwenLLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"OPENAI_API_KEY": "OpenAI API key"}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.QWEN

    def _create_model(self):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise LLMProviderError(
                "langchain_openai not installed. Run: pip install langchain-openai"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("OPENAI_API_KEY")

        return ChatOpenAI(**model_config)


class ClaudeLLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"ANTHROPIC_API_KEY": "Anthropic API key for Claude"}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.CLAUDE

    def _create_model(self):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise LLMProviderError(
                "langchain_anthropic not installed. Run: pip install langchain-anthropic"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("ANTHROPIC_API_KEY")

        return ChatAnthropic(**model_config)


class OpenAILLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"OPENROUTER_API_KEY": "Openrouter API key "}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.OPENAI

    def _create_model(self):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise LLMProviderError(
                "langchain_openai not installed. Run: pip install langchain-openai"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("OPENROUTER_API_KEY")

        return ChatOpenAI(**model_config)


class MistralLLM(LLMProvider):
    def _get_required_env_vars(self) -> Dict[str, str]:
        return {"MISTRAL_API_KEY": "MISTRAL API key for Claude"}

    def get_provider_type(self) -> LLMArchitecture:
        return LLMArchitecture.MISTRAL

    def _create_model(self):
        try:
            from langchain_mistralai import ChatMistralAI
        except ImportError:
            raise LLMProviderError(
                "langchain_mistralai not installed. Run: pip install langchain-mistralai"
            )

        model_config = self.config.to_dict()
        model_config["api_key"] = os.getenv("MISTRAL_API_KEY")

        return ChatMistralAI(**model_config)
