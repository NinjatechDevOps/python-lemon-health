from app.llm.groq_llm import GroqLLM
from app.llm.google_llm import GoogleLLM

def get_llm_provider(provider_name: str):
    providers = {
        "groq": GroqLLM,
        "google": GoogleLLM
    }

    provider = providers.get(provider_name.lower())
    if provider is None:
        raise ValueError(f"Unsupported provider: {provider_name}")

    return provider()