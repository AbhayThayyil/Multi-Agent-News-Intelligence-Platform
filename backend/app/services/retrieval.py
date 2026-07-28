import logging

from app.graph.state import GraphState
from app.tools.base import NewsSourceTool
from app.tools.rss import get_rss_tool

logger = logging.getLogger(__name__)


def retrieval_node(state: GraphState) -> GraphState:
    tool: NewsSourceTool = get_rss_tool()
    articles = tool.fetch()

    usable = [article for article in articles if article.content]
    if len(usable) < len(articles):
        logger.info(
            "Dropping %s of %s articles with no content", len(articles) - len(usable), len(articles)
        )

    return {"articles": [article.model_dump(mode="json") for article in usable]}
