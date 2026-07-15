from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.planner import planner_node
from app.agents.summarizer import summarizer_node
from app.graph.state import GraphState
from app.services.response_composer import response_composer_node
from app.services.retrieval import retrieval_node


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("response_composer", response_composer_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "retrieval")
    builder.add_edge("retrieval", "summarizer")
    builder.add_edge("summarizer", "response_composer")
    builder.add_edge("response_composer", END)

    return builder.compile()
