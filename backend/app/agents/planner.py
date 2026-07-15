from app.graph.state import GraphState


def planner_node(state: GraphState) -> GraphState:
    return {"execution_plan": ["retrieve", "summarize"]}
