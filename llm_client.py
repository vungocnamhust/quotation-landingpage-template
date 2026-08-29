import os
import httpx
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()

# A hung provider call must never block a Fast Track request forever (16.3 F-06).
# Per-request read timeout; pydantic_ai's retries stay bounded on top of it.
_LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(_LLM_TIMEOUT_SECONDS, connect=10.0)
        )
    return _http_client

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
        api_key=api_key,
        http_client=_get_http_client(),
    )

    return OpenAIChatModel(
        model_name,
        provider=provider,
        settings={"extra_body": {"thinking": {"type": "disabled"}}},
    )

