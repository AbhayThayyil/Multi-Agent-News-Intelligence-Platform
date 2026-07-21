import logging
import time
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

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM client cannot produce a completion, regardless of
    which underlying provider or library caused it."""


class LLMClient:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str) -> str:
        started_at = time.monotonic()
        logger.info("Calling LLM model=%s", self._model)
        try:
            response = completion(
                model=f"openrouter/{self._model}",
                api_key=self._api_key,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
                num_retries=2,
            )
        except AuthenticationError as e:
            logger.error("LLM call failed: invalid API key")
            raise LLMError("Invalid OpenRouter API key") from e
        except (NotFoundError, BadRequestError) as e:
            logger.error("LLM call failed: model '%s' unavailable or invalid", self._model)
            raise LLMError(f"Model '{self._model}' is unavailable or invalid") from e
        except RateLimitError as e:
            logger.error("LLM call failed: rate limit exceeded after retries")
            raise LLMError("Rate limit exceeded, even after automatic retries") from e
        except Timeout as e:
            logger.error("LLM call failed: timed out after retries")
            raise LLMError("LLM request timed out, even after automatic retries") from e
        except (APIConnectionError, ServiceUnavailableError, InternalServerError) as e:
            logger.error("LLM call failed: provider unavailable after retries")
            raise LLMError("LLM provider unavailable, even after automatic retries") from e
        except Exception as e:
            logger.error("LLM call failed: unexpected error: %s", e)
            raise LLMError(f"Unexpected error calling the LLM: {e}") from e

        elapsed = time.monotonic() - started_at
        logger.info("LLM call succeeded model=%s duration=%.2fs", self._model, elapsed)
        return response.choices[0].message.content


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
