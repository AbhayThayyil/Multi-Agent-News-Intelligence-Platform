from functools import lru_cache

from litellm import completion

from app.config.settings import get_settings


class LLMClient:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str) -> str:
        response = completion(
            model=f"openrouter/{self._model}",
            api_key=self._api_key,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
