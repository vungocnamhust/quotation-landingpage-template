import os
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()

def get_model() -> OpenAIChatModel:
    """
    Initializes and returns the OpenAIChatModel configured for DeepSeek.
    Reads config from environment variables:
      - DEEPSEEK_API_KEY
      - DEEPSEEK_API_BASE
      - DEEPSEEK_MODEL (defaults to 'deepseek-chat')
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key or api_key == "sk-your-deepseek-key-here":
        # Fallback to OpenAI API key if present, or raise warning
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and not openai_key.startswith("sk-your-"):
            print("[Warning] DEEPSEEK_API_KEY is not set or placeholder. Falling back to OPENAI_API_KEY.")
            api_key = openai_key
            # If using OpenAI fallback, we should also default model and base URL to OpenAI standard
            base_url = "https://api.openai.com/v1"
            model_name = "gpt-4o-mini"
        else:
            print("[Error] Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY is set. Please check your .env file.")

    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key
    )

    return OpenAIChatModel(
        model_name,
        provider=provider,
        settings={"extra_body": {"thinking": {"type": "disabled"}}},
    )

