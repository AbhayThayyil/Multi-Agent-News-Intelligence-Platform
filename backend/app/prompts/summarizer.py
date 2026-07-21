SUMMARIZER_INSTRUCTIONS = (
    "You are a news summarization assistant. Summarize the following "
    "articles into a concise, neutral paragraph covering the key points. "
    "Do not include your own opinions or unrelated information."
)


def build_summarizer_prompt(articles: list[dict]) -> str:
    formatted_articles = "\n".join(
        f"- {article['title']} (Source: {article['source']})"
        for article in articles
    )
    return f"{SUMMARIZER_INSTRUCTIONS}\n\nArticles:\n{formatted_articles}\n\nSummary:"
