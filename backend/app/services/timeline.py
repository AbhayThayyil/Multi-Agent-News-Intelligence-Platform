import logging
from datetime import timezone

from app.schemas.article import Article

logger = logging.getLogger(__name__)

TIMELINE_ARTICLE_CAP = 10


def normalize_to_utc(article: Article) -> Article:
    if article.published_at is not None and article.published_at.tzinfo is None:
        return article.model_copy(
            update={"published_at": article.published_at.replace(tzinfo=timezone.utc)}
        )
    return article


def filter_dated_articles(articles: list[Article]) -> list[Article]:
    dated = []
    for article in articles:
        if article.published_at is None:
            logger.info("Dropping article with no published_at from timeline: %r", article.title)
            continue
        dated.append(article)
    return dated


def sort_chronologically(articles: list[Article]) -> list[Article]:
    return sorted(articles, key=lambda a: a.published_at)


def cap_to_most_recent(articles: list[Article], cap: int = TIMELINE_ARTICLE_CAP) -> list[Article]:
    return articles[-cap:]


def select_timeline_articles(articles: list[dict]) -> list[Article]:
    parsed = [normalize_to_utc(Article(**article_dict)) for article_dict in articles]
    dated = filter_dated_articles(parsed)
    ordered = sort_chronologically(dated)
    return cap_to_most_recent(ordered)
