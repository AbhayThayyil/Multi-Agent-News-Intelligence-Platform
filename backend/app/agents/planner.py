import json

from pydantic import ValidationError

from app.graph.state import GraphState
from app.llm.client import get_llm_client
from app.prompts.planner import build_planner_prompt
from app.schemas.execution_plan import ExecutionPlan


class PlannerOutputError(Exception):
    """Raised when the Planner's raw LLM output cannot be parsed into a
    valid ExecutionPlan, regardless of whether the problem was invalid
    JSON syntax, a non-object JSON value, or a schema mismatch."""


def parse_execution_plan(raw_output: str) -> ExecutionPlan:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise PlannerOutputError(f"Planner output was not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise PlannerOutputError(
            f"Planner output was valid JSON but not a JSON object: {raw_output!r}"
        )

    try:
        return ExecutionPlan(**parsed)
    except ValidationError as e:
        raise PlannerOutputError(f"Planner output did not match ExecutionPlan schema: {e}") from e


def planner_node(state: GraphState) -> GraphState:
    prompt = build_planner_prompt(state["query"])
    client = get_llm_client()
    raw_output = client.complete(prompt, json_mode=True)
    plan = parse_execution_plan(raw_output)
    return {"execution_plan": plan}
