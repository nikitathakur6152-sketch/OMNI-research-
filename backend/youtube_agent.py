from app.services.llm import chat
from app.services.youtube import transcript_for

def run(question: str, url: str):
    vid, transcript = transcript_for(url)
    answer = chat(
        "Analyze the supplied YouTube transcript only. Summarize clearly and use timestamps when present. State when information is not in the transcript.",
        f"Video: https://www.youtube.com/watch?v={vid}\nQuestion: {question}\n\nTranscript:\n{transcript}"
    )
    return answer, [{"title": "YouTube transcript", "url": f"https://www.youtube.com/watch?v={vid}"}]
