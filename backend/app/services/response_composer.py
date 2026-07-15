from app.graph.state import GraphState


def response_composer_node(state: GraphState) -> GraphState:
    return {
        "response": {
            "answer": state["summary"],
            "sources": state["articles"],
        }
    }
