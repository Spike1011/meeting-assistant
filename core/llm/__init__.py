from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider
from .chatgpt_provider import ChatGPTProvider
from core.config_manager import ConfigManager

def create_llm_provider(config: ConfigManager) -> LLMProvider:
    """
    Factory function to create an LLM provider based on configuration.
    """
    provider_type = config.get_llm_provider_type()
    model_name = config.get_llm_model_name()
    api_key = config.get_llm_api_key(provider_type)
    
    if provider_type == "gemini":
        return GeminiProvider(api_key=api_key, model_name=model_name)
    elif provider_type == "deepseek":
        return DeepSeekProvider(api_key=api_key, model_name=model_name)
    elif provider_type == "chatgpt":
        return ChatGPTProvider(api_key=api_key, model_name=model_name)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
