# Local Wiki AI

A fully local ChatGPT-style chat app powered by **Qwen2.5 (14B)** running through **Ollama**,
grounded in your own wiki content stored in an external **SQLite** database, with chat
session history also stored in SQLite.

## Architecture

- **Model serving**: [Ollama](https://ollama.com) runs Qwen2.5:14b locally and exposes
  `http://localhost:11434`. Model weights are downloaded once and cached by Ollama.
- **Backend**: FastAPI ([backend/main.py](backend/main.py)) exposes a chat/session API,
  streams model output, and does simple keyword-based retrieval (RAG) against your wiki DB.
- **Wiki DB** ([backend/wiki_db.py](backend/wiki_db.py)): opens your existing SQLite file
  **read-only**, auto-detects tables/text columns (no fixed schema required), and searches
  them for context relevant to each question.
- **Chat history DB** ([backend/chat_db.py](backend/chat_db.py)): a separate local SQLite
  file (`data/chat_history.db`) storing sessions + messages, so conversations persist
  across restarts.
- **Frontend** ([frontend/](frontend/)): plain HTML/CSS/JS, ChatGPT-like layout (sidebar
  with sessions, streaming assistant replies, auto-titled chats).

## 1. Install Ollama and download the model

```powershell
./scripts/pull_model.ps1
```

This installs/launches Ollama and runs `ollama pull qwen2.5:14b` (downloads the model to
Ollama's local model store, ~9 GB). Requires a GPU/CPU with enough RAM (14B model is
comfortable with 16GB+ system RAM, more if you want full GPU offload).

## 2. Point the app at your wiki SQLite database

Edit [config/config.yaml](config/config.yaml):

```yaml
wiki_db:
  path: "D:\\somewhere\\on\\disk\\your-wiki.db"
```

The path can be anywhere on your Windows filesystem. The schema is auto-detected, so no
column/table names need to match anything specific — it looks for text-like columns across
all tables and searches them by keyword.

## 3. Install Python dependencies

```powershell
./scripts/setup.ps1
```

## 4. Run

Make sure Ollama is running (it normally runs as a background service after install;
otherwise start it with `ollama serve`), then:

```powershell
./scripts/start.ps1
```

Open **http://127.0.0.1:8000** in your browser — a ChatGPT-style chat UI backed entirely
by your local model and data.

## Notes

- Conversation history for the current session is sent back to Qwen2.5 on every turn (up
  to the last 40 messages) so the model has full context of the ongoing chat.
- All sessions/messages persist in `data/chat_history.db` — delete that file to reset history.
- The wiki DB is opened strictly read-only; the app never writes to it.
- Change `ollama.model` in config.yaml to use a different tag (e.g. `qwen2.5:14b-instruct-q4_K_M`)
  if you want a smaller/quantized variant for lower memory usage.
