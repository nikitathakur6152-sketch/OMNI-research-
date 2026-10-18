from typing import Optional


def route_task(message: str, requested: str, youtube_url: Optional[str] = None) -> str:
    if requested != "auto":
        return requested
    text = message.lower()
    if youtube_url or "youtube.com/" in text or "youtu.be/" in text:
        return "youtube"
    if any(x in text for x in ["write code", "generate code", "debug this", "python code", "javascript code", "implement "]):
        return "code"
    if any(x in text for x in ["research", "latest", "current", "sources", "search the web", "on the internet"]):
        return "research"
    return "chat"
