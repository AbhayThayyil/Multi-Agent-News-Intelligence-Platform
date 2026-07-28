from app.graph.state import GraphState
from app.tools.base import NewsSourceTool
from app.tools.rss import get_rss_tool


def retrieval_node(state: GraphState) -> GraphState:
    tool: NewsSourceTool = get_rss_tool()
    articles = tool.fetch()
    return {"articles": [article.model_dump() for article in articles]}
