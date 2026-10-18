from tavily import TavilyClient
from app.config import TAVILY_API_KEY

def search_web(query: str, max_results: int = 6) -> list[dict]:
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is missing in backend/.env")
    result = TavilyClient(api_key=TAVILY_API_KEY).search(
        query=query, max_results=max_results, search_depth="advanced"
    )
    return [
        {"title": x.get("title", "Untitled"), "url": x.get("url", ""),
         "snippet": x.get("content", "")[:1200]}
        for x in result.get("results", [])
    ]
