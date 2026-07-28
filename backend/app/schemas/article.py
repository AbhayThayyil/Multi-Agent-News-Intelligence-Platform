from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    title: str = Field(min_length=1)
    content: str | None = None
    published_at: datetime | None = None
    source: str
    url: HttpUrl | None = None
