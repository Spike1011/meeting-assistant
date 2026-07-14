from typing import Optional

from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider
from .chatgpt_provider import ChatGPTProvider
from core.config_manager import ConfigManager


def _default_model_for_provider(provider_type: str) -> str:
    """
    Возвращает разумную модель по умолчанию для каждого провайдера,
    когда выбран провайдер, отличный от того, что прописан в config.json.
    """
    if provider_type == "gemini":
        return "gemini-2.0-flash"
    if provider_type == "deepseek":
        return "deepseek-chat"
    if provider_type == "chatgpt":
        return "gpt-4o"
    return ""


def create_llm_provider(
    config: ConfigManager,
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
) -> LLMProvider:
    """
    Factory function to create an LLM provider based on configuration.
    Optionally allows overriding provider type and model name.

    Важно: если в API запрашивается провайдер, отличный от того, что в config.json,
    и модель не указана явно, берётся дефолтная модель для этого провайдера,
    чтобы избежать ситуаций вида 'gemini-2.0-flash' в OpenAI/DeepSeek.
    """
    config_provider = config.get_llm_provider_type()

    if provider_type is None:
        provider_type = config_provider

    if model_name is None:
        if provider_type == config_provider:
            # Используем то, что прописано в конфиге
            model_name = config.get_llm_model_name()
        else:
            # Переопределили провайдера (например, через API) — подставим его дефолтную модель
            model_name = _default_model_for_provider(provider_type)

    api_key = config.get_llm_api_key(provider_type)

    if provider_type == "gemini":
        return GeminiProvider(api_key=api_key, model_name=model_name)
    elif provider_type == "deepseek":
        return DeepSeekProvider(api_key=api_key, model_name=model_name)
    elif provider_type == "chatgpt":
        return ChatGPTProvider(api_key=api_key, model_name=model_name)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
