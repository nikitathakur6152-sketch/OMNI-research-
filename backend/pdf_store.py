import uuid
from typing import Optional
import fitz
import chromadb
from sentence_transformers import SentenceTransformer

_client = chromadb.Client()
_collection = _client.get_or_create_collection("omniresearch_docs")
_embedder = None
_docs: dict[str, dict] = {}

def _model():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def _chunks(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    text = " ".join(text.split())
    return [text[i:i+size] for i in range(0, len(text), size-overlap) if text[i:i+size]]

def ingest_pdf(filename: str, raw: bytes) -> tuple[str, int]:
    pdf = fitz.open(stream=raw, filetype="pdf")
    pieces = []
    for page_num, page in enumerate(pdf, 1):
        pieces.extend((chunk, page_num) for chunk in _chunks(page.get_text()))
    pdf.close()
    if not pieces:
        raise ValueError("No extractable text found. Scanned PDFs need OCR support.")
    doc_id = str(uuid.uuid4())
    vectors = _model().encode([p[0] for p in pieces], normalize_embeddings=True).tolist()
    _collection.add(
        ids=[f"{doc_id}-{i}" for i in range(len(pieces))],
        documents=[p[0] for p in pieces],
        embeddings=vectors,
        metadatas=[{"document_id": doc_id, "filename": filename, "page": p[1]} for p in pieces],
    )
    _docs[doc_id] = {"filename": filename, "chunks": len(pieces)}
    return doc_id, len(pieces)

def query_documents(question: str, document_ids: Optional[list[str]] = None, n: int = 5):
    if not _docs:
        return [], []
    vector = _model().encode([question], normalize_embeddings=True).tolist()[0]
    where = {"document_id": {"$in": document_ids}} if document_ids else None
    result = _collection.query(query_embeddings=[vector], n_results=min(n, _collection.count()), where=where)
    chunks, sources = [], []
    for text, meta in zip(result["documents"][0], result["metadatas"][0]):
        chunks.append(text)
        source = {"title": meta["filename"], "page": meta["page"], "document_id": meta["document_id"]}
        if source not in sources:
            sources.append(source)
    return chunks, sources

def list_documents():
    return [{"document_id": k, **v} for k, v in _docs.items()]
