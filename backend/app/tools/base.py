from typing import Protocol

from app.schemas.article import Article


class NewsSourceTool(Protocol):
    def fetch(self) -> list[Article]: ...
