from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    openrouter_api_key: str = Field(min_length=1)
    llm_model: str = "openai/gpt-oss-20b:free"

    rss_feed_url: str = "http://feeds.bbci.co.uk/news/rss.xml"
    rss_source_name: str = "BBC News"

    @field_validator("openrouter_api_key")
    @classmethod
    def strip_and_check_api_key(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("OPENROUTER_API_KEY is set but blank")
        return stripped


@lru_cache
def get_settings() -> Settings:
    return Settings()
