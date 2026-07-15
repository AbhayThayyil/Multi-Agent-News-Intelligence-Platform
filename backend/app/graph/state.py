from typing import TypedDict


class GraphState(TypedDict, total=False):
    query: str
    execution_plan: list[str]
    articles: list[dict]
    summary: str
    response: dict
