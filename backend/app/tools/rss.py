from datetime import datetime, timezone
from functools import lru_cache

import feedparser
import httpx

from app.config.settings import get_settings
from app.schemas.article import Article


class RSSToolError(Exception):
    """Raised when the RSS tool cannot fetch or parse a feed, regardless of
    which underlying library or network failure caused it."""


class RSSTool:
    def __init__(self, feed_url: str, source: str):
        self._feed_url = feed_url
        self._source = source

    def fetch(self) -> list[Article]:
        try:
            response = httpx.get(self._feed_url, timeout=15, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RSSToolError(f"Failed to fetch RSS feed '{self._feed_url}': {e}") from e

        parsed = feedparser.parse(response.content)
        if parsed.bozo:
            raise RSSToolError(
                f"Failed to parse RSS feed '{self._feed_url}': {parsed.bozo_exception}"
            )

        return [self._to_article(entry) for entry in parsed.entries]

    def _to_article(self, entry: dict) -> Article:
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        return Article(
            title=entry.get("title", ""),
            content=entry.get("summary"),
            published_at=published_at,
            source=self._source,
            url=entry.get("link"),
        )


@lru_cache
def get_rss_tool() -> RSSTool:
    settings = get_settings()
    return RSSTool(feed_url=settings.rss_feed_url, source=settings.rss_source_name)
