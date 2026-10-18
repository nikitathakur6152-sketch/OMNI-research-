import re
import sqlite3
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.config import FRONTEND_ORIGIN, MAX_UPLOAD_MB
from app.config import DEVELOPER_EMAILS
from app.db import (
    create_session,
    create_user,
    get_db_connection,
    get_user_by_email,
    get_user_by_token,
    init_db,
    verify_password,
    save_chat,
    list_chat_history,
    record_auth_event,
    list_auth_events,
    revoke_session,
)
from app.agents.supervisor import route_task
from app.agents.research_agent import run as research
from app.agents.pdf_agent import run as pdf_chat
from app.agents.youtube_agent import run as youtube_chat
from app.agents.code_agent import run as code_chat
from app.services.pdf_store import ingest_pdf, list_documents
from app.services.llm import chat as llm_chat

app = FastAPI(title="OmniResearch AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173"}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    task: str = "auto"
    youtube_url: Optional[str] = None
    document_ids: list[str] = Field(default_factory=list)


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=6, max_length=200)


@app.get("/")
def root():
    return {"name": "OmniResearch AI", "status": "running", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    if not req.name.strip():
        raise HTTPException(400, "Name is required.")
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(400, "Email is required.")
    try:
        user = create_user(req.name.strip(), email, req.password)
    except sqlite3.IntegrityError:
        raise HTTPException(400, "An account with that email already exists.")
    token = create_session(user["id"])
    record_auth_event(user["id"], "signup")
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "is_developer": user["email"] in DEVELOPER_EMAILS}}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    token = create_session(user["id"])
    record_auth_event(user["id"], "login")
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "is_developer": user["email"] in DEVELOPER_EMAILS}}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    user = get_user_by_token(token)
    if user is None:
        raise HTTPException(401, "Invalid or expired session.")
    record_auth_event(user["id"], "logout")
    revoke_session(token)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    user = get_user_by_token(token)
    if user is None:
        raise HTTPException(401, "Invalid or expired session.")
    return {"user": {**user, "is_developer": user["email"] in DEVELOPER_EMAILS}}


@app.get("/api/documents")
def documents():
    return {"documents": list_documents()}


def authenticated_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token.")
    user = get_user_by_token(authorization.split(" ", 1)[1].strip())
    if user is None:
        raise HTTPException(401, "Invalid or expired session.")
    return user


@app.get("/api/history")
def history(authorization: Optional[str] = Header(default=None)):
    user = authenticated_user(authorization)
    return {"history": list_chat_history(user["id"])}


@app.get("/api/developer/auth-events")
def auth_events(authorization: Optional[str] = Header(default=None)):
    user = authenticated_user(authorization)
    if user["email"] not in DEVELOPER_EMAILS:
        raise HTTPException(403, "Developer access is required.")
    return {"events": list_auth_events()}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_MB} MB limit.")
    try:
        doc_id, chunks = ingest_pdf(file.filename, raw)
        return {"document_id": doc_id, "filename": file.filename, "chunks": chunks}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, authorization: Optional[str] = Header(default=None)):
    user = authenticated_user(authorization)
    task = route_task(req.message, req.task, req.youtube_url)
    try:
        if task == "research":
            answer, sources = research(req.message)
            save_chat(user["id"], task, req.message, answer)
            return {"answer": answer, "task": task, "sources": sources}
        if task == "pdf":
            answer, sources = pdf_chat(req.message, req.document_ids or None)
            save_chat(user["id"], task, req.message, answer)
            return {"answer": answer, "task": task, "sources": sources}
        if task == "youtube":
            url = req.youtube_url
            if not url:
                match = re.search(r"https?://\S+", req.message)
                url = match.group(0).rstrip(").,") if match else None
            if not url:
                raise HTTPException(400, "Paste a YouTube URL and ask your question.")
            answer, sources = youtube_chat(req.message, url)
            save_chat(user["id"], task, req.message, answer)
            return {"answer": answer, "task": task, "sources": sources}
        if task == "code":
            answer = code_chat(req.message)
            save_chat(user["id"], task, req.message, answer)
            return {"answer": answer, "task": task, "sources": []}
        answer = llm_chat(
            "You are OmniResearch AI, a helpful assistant. For up-to-date facts, suggest Web Research mode.",
            req.message,
        )
        save_chat(user["id"], "chat", req.message, answer)
        return {"answer": answer, "task": "chat", "sources": []}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, str(exc))
