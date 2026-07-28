import logging
from datetime import datetime, timezone
from functools import lru_cache

import feedparser
import httpx
from pydantic import ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config.settings import get_settings
from app.schemas.article import Article

logger = logging.getLogger(__name__)


class RSSToolError(Exception):
    """Raised when the RSS tool cannot fetch or parse a feed, regardless of
    which underlying library or network failure caused it."""


def _is_retryable(exception: BaseException) -> bool:
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500
    return False


class RSSTool:
    def __init__(self, feed_url: str, source: str):
        self._feed_url = feed_url
        self._source = source

    def fetch(self) -> list[Article]:
        try:
            response = self._fetch_with_retry()
        except httpx.HTTPStatusError as e:
            logger.error("RSS fetch failed: %s returned %s", self._feed_url, e.response.status_code)
            raise RSSToolError(
                f"RSS feed '{self._feed_url}' returned {e.response.status_code}"
            ) from e
        except httpx.HTTPError as e:
            logger.error("RSS fetch failed after retries: %s", e)
            raise RSSToolError(
                f"Failed to fetch RSS feed '{self._feed_url}' after retries: {e}"
            ) from e

        parsed = feedparser.parse(response.content)
        if parsed.bozo:
            logger.error("RSS parse failed: %s", parsed.bozo_exception)
            raise RSSToolError(
                f"Failed to parse RSS feed '{self._feed_url}': {parsed.bozo_exception}"
            )

        articles = []
        for entry in parsed.entries:
            try:
                articles.append(self._to_article(entry))
            except ValidationError as e:
                logger.warning("Skipping malformed RSS entry from %s: %s", self._feed_url, e)

        logger.info(
            "RSS fetch succeeded: %s of %s entries usable from %s",
            len(articles),
            len(parsed.entries),
            self._feed_url,
        )
        return articles

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _fetch_with_retry(self) -> httpx.Response:
        response = httpx.get(self._feed_url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        return response

    def _to_article(self, entry: dict) -> Article:
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        return Article(
            title=entry.get("title", ""),
            content=entry.get("summary"),
            published_at=published_at,
            source=self._source,
            url=entry.get("link") or None,
        )


@lru_cache
def get_rss_tool() -> RSSTool:
    settings = get_settings()
    return RSSTool(feed_url=settings.rss_feed_url, source=settings.rss_source_name)
