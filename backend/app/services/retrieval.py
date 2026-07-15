from app.graph.state import GraphState


def retrieval_node(state: GraphState) -> GraphState:
    return {
        "articles": [
            {"title": "Mock Article", "source": "Mock RSS"},
        ]
    }
