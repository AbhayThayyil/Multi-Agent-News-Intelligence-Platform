import json

from app.graph.state import GraphState
from app.llm.client import get_llm_client
from app.prompts.planner import build_planner_prompt
from app.schemas.execution_plan import ExecutionPlan


def planner_node(state: GraphState) -> GraphState:
    prompt = build_planner_prompt(state["query"])
    client = get_llm_client()
    raw_output = client.complete(prompt, json_mode=True)
    parsed = json.loads(raw_output)
    plan = ExecutionPlan(**parsed)
    return {"execution_plan": plan}
