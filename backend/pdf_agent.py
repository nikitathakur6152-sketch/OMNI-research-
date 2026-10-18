from typing import Optional
from app.services.llm import chat
from app.services.pdf_store import query_documents

def run(question: str, document_ids: Optional[list[str]] = None):
    chunks, sources = query_documents(question, document_ids)
    if not chunks:
        return "No indexed PDF text found. Upload a text-based PDF first.", []
    context = "\n\n".join(f"Excerpt {i+1}: {x}" for i, x in enumerate(chunks))
    answer = chat(
        "Answer only from the provided PDF excerpts. If the answer is absent, say so. Mention source page numbers when useful.",
        f"Question: {question}\n\nExcerpts:\n{context}"
    )
    return answer, sources
