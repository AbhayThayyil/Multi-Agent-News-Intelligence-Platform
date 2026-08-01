from typing import TypedDict

from app.schemas.execution_plan import ExecutionPlan


class GraphState(TypedDict, total=False):
    query: str
    execution_plan: ExecutionPlan
    articles: list[dict]
    summary: str
    response: dict
