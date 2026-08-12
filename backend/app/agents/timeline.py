from app.graph.state import GraphState


def timeline_node(state: GraphState) -> GraphState:
    return {"timeline": [{"date": "Mock Date", "event": "Mock Event"}]}
