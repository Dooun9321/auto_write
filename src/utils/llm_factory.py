"""LLM Factory for creating LLM instances based on provider"""

from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMFactory:
    """Factory class for creating LLM instances"""

    @staticmethod
    def create_llm(config: Dict, temperature: float = 0.2):
        """
        Create an LLM instance based on configuration

        Args:
            config: Configuration dictionary with 'provider', 'api_key', 'model'
            temperature: Temperature for generation

        Returns:
            LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
        """
        provider = config.get("provider", "openai").lower()
        api_key = config.get("api_key")
        model = config.get("model")

        if not api_key:
            raise ValueError(f"API key not provided for {provider}")

        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-pro",
                google_api_key=api_key,
                temperature=temperature,
                convert_system_message_to_human=True,  # Gemini compatibility
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model or "gpt-4o",
                api_key=api_key,
                temperature=temperature,
            )
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. Supported providers: openai, gemini"
            )

    @staticmethod
    def create_query_generator_llm(config: Dict):
        """Create LLM for query generation (low temperature)"""
        return LLMFactory.create_llm(config, temperature=0.1)

    @staticmethod
    def create_analysis_llm(config: Dict):
        """Create LLM for analysis (medium temperature)"""
        return LLMFactory.create_llm(config, temperature=0.2)

    @staticmethod
    def create_documentation_llm(config: Dict):
        """Create LLM for documentation generation (medium temperature)"""
        return LLMFactory.create_llm(config, temperature=0.3)
