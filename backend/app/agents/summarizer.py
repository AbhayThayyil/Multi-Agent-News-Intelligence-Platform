from app.graph.state import GraphState
from app.llm.client import get_llm_client
from app.prompts.summarizer import build_summarizer_prompt


def summarizer_node(state: GraphState) -> GraphState:
    prompt = build_summarizer_prompt(state["articles"])
    client = get_llm_client()
    summary = client.complete(prompt)
    return {"summary": summary}
