from app.graph.state import GraphState
from app.schemas.execution_plan import ExecutionPlan


def planner_node(state: GraphState) -> GraphState:
    return {"execution_plan": ExecutionPlan(intent="summary", requires_timeline=False)}
