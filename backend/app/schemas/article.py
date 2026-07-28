from datetime import datetime

from pydantic import BaseModel


class Article(BaseModel):
    title: str
    content: str | None = None
    published_at: datetime | None = None
    source: str
    url: str | None = None
