"""FastAPI app: chat sessions/history API + streaming chat against local Ollama (Qwen2.5),
augmented with context pulled from a configurable external SQLite wiki DB.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import load_config
from .chat_db import ChatHistoryDB
from .wiki_db import WikiDB
from .ollama_client import OllamaClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

cfg = load_config()
chat_db = ChatHistoryDB(cfg.chat_history.path)
wiki_db = WikiDB(
    cfg.wiki_db.path,
    search_limit_per_table=cfg.wiki_db.search_limit_per_table,
    max_context_chars=cfg.wiki_db.max_context_chars,
) if cfg.wiki_db.enabled else None
ollama = OllamaClient(
    host=cfg.ollama.host,
    model=cfg.ollama.model,
    temperature=cfg.ollama.temperature,
    num_ctx=cfg.ollama.num_ctx,
)

MAX_HISTORY_MESSAGES = 40
SYSTEM_PROMPT = (
    "You are a helpful local assistant. Answer using the conversation history for context. "
    "If a 'Knowledge base context' section is provided below, prefer it when relevant to the "
    "question; otherwise answer from your own knowledge. Keep answers concise and accurate."
)

app = FastAPI(title="Local Wiki AI")


class CreateSessionRequest(BaseModel):
    title: str = "New chat"


class RenameSessionRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/api/health")
async def health():
    return {
        "ollama_reachable": await ollama.is_reachable(),
        "ollama_model": cfg.ollama.model,
        "wiki_db_available": bool(wiki_db and wiki_db.available),
        "wiki_db_path": str(cfg.wiki_db.path),
    }


@app.get("/api/sessions")
async def list_sessions():
    return chat_db.list_sessions()


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest):
    return chat_db.create_session(title=req.title)


@app.patch("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameSessionRequest):
    if not chat_db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    chat_db.rename_session(session_id, req.title)
    return {"ok": True}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if not chat_db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    chat_db.delete_session(session_id)
    return {"ok": True}


@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    if not chat_db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_db.get_messages(session_id)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not chat_db.session_exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    chat_db.add_message(req.session_id, "user", user_message)

    # Auto-title new sessions from the first user message, ChatGPT-style.
    history = chat_db.get_messages(req.session_id)
    if len([m for m in history if m["role"] == "user"]) == 1:
        title = user_message[:60] + ("..." if len(user_message) > 60 else "")
        chat_db.rename_session(req.session_id, title)

    wiki_context = wiki_db.search(user_message) if wiki_db else ""

    system_content = SYSTEM_PROMPT
    if wiki_context:
        system_content += f"\n\nKnowledge base context:\n{wiki_context}"

    messages = [{"role": "system", "content": system_content}]
    for m in history[-MAX_HISTORY_MESSAGES:]:
        messages.append({"role": m["role"], "content": m["content"]})

    async def generate():
        full_response_parts: list[str] = []
        try:
            async for chunk in ollama.stream_chat(messages):
                full_response_parts.append(chunk)
                yield chunk
        except Exception as exc:  # surface a readable error to the chat UI
            err_text = f"\n\n[Error contacting local model: {exc}]"
            full_response_parts.append(err_text)
            yield err_text
        finally:
            full_response = "".join(full_response_parts).strip()
            if full_response:
                chat_db.add_message(req.session_id, "assistant", full_response)

    return StreamingResponse(generate(), media_type="text/plain")


# Serve the chat UI (index.html, style.css, app.js) as static files.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
