from apps.llm.groq_llm import GroqLLM
from apps.llm.google_llm import GoogleLLM
from apps.llm.openai_llm import OpenAILLM

def get_llm_provider(provider_name: str):
    providers = {
        "groq": GroqLLM,
        "google": GoogleLLM,
        "openai": OpenAILLM
    }

    provider = providers.get(provider_name.lower())
    if provider is None:
        raise ValueError(f"Unsupported provider: {provider_name}")

    return provider()