from app.graph.state import GraphState


def retrieval_node(state: GraphState) -> GraphState:
    return {
        "articles": [
            {
                "title": "Mock Article",
                "source": "Mock RSS",
                "content": (
                    "Researchers announced a new open-weight language model "
                    "today, claiming improved reasoning benchmarks over prior "
                    "versions while requiring less compute to run."
                ),
            },
        ]
    }
