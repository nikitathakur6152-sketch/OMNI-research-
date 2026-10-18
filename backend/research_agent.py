from app.services.llm import chat
from app.services.web_search import search_web

def run(question: str):
    sources = search_web(question)
    if not sources:
        return "No useful web results found. Try a more specific query.", []
    context = "\n\n".join(
        f"[{i}] {s['title']}\nURL: {s['url']}\nSnippet: {s['snippet']}"
        for i, s in enumerate(sources, 1)
    )
    answer = chat(
        "You are a careful research assistant. Synthesize the supplied search snippets, cite claims as [1], [2], etc. Never invent source details. Note uncertainty.",
        f"Question: {question}\n\nSearch results:\n{context}"
    )
    return answer, sources
