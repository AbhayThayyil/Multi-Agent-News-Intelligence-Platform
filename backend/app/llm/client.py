from functools import lru_cache

from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from app.config.settings import get_settings


class LLMError(Exception):
    """Raised when the LLM client cannot produce a completion, regardless of
    which underlying provider or library caused it."""


class LLMClient:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str) -> str:
        try:
            response = completion(
                model=f"openrouter/{self._model}",
                api_key=self._api_key,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
                num_retries=2,
            )
        except AuthenticationError as e:
            raise LLMError("Invalid OpenRouter API key") from e
        except (NotFoundError, BadRequestError) as e:
            raise LLMError(f"Model '{self._model}' is unavailable or invalid") from e
        except RateLimitError as e:
            raise LLMError("Rate limit exceeded, even after automatic retries") from e
        except Timeout as e:
            raise LLMError("LLM request timed out, even after automatic retries") from e
        except (APIConnectionError, ServiceUnavailableError, InternalServerError) as e:
            raise LLMError("LLM provider unavailable, even after automatic retries") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling the LLM: {e}") from e

        return response.choices[0].message.content


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
