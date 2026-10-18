#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "$FRONTEND_PID" ]]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.9 or newer is required. Install Python, then run ./start.sh again."
  exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
  echo "Python 3.9 or newer is required."
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 20 or newer is required. Install Node.js, then run ./start.sh again."
  exit 1
fi
if ! node -e 'const [major] = process.versions.node.split(".").map(Number); process.exit(major < 20 ? 1 : 0)'; then
  echo "Node.js 20 or newer is required."
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "Created backend/.env. Add API keys there to enable AI features."
fi

if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  echo "Creating the backend virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi

if ! "$BACKEND_DIR/.venv/bin/python" -c 'import fastapi, uvicorn, multipart, dotenv, mistralai, tavily, fitz, chromadb, sentence_transformers, youtube_transcript_api' >/dev/null 2>&1; then
  echo "Installing backend dependencies (PDF support includes ML packages)..."
  "$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm ci)
fi

# Preserve a damaged database before initializing a clean one. SQLite cannot
# serve requests from a malformed file, and replacing it without a backup would
# discard the only remaining copy of local account data.
if [[ -f "$BACKEND_DIR/app.db" ]] && ! "$BACKEND_DIR/.venv/bin/python" - "$BACKEND_DIR/app.db" <<'PY'
import sqlite3
import sys

try:
    connection = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
    result = connection.execute("PRAGMA quick_check").fetchone()
    connection.close()
    raise SystemExit(0 if result and result[0] == "ok" else 1)
except sqlite3.DatabaseError:
    raise SystemExit(1)
PY
then
  DB_BACKUP="$BACKEND_DIR/app.db.corrupt.$(date +%Y%m%d-%H%M%S)"
  cp -p "$BACKEND_DIR/app.db" "$DB_BACKUP"
  rm "$BACKEND_DIR/app.db"
  echo "The local database was damaged. Preserved the original at $DB_BACKUP. A fresh database will be created."
fi

(cd "$BACKEND_DIR" && .venv/bin/python -c 'from app.db import init_db; init_db()')

if curl --max-time 1 -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "Backend is already healthy on port 8000; reusing it."
elif command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  PORT_OWNER="$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t | tr '\n' ' ')"
  echo "Port 8000 is occupied by PID(s) $PORT_OWNER, but no OmniResearch API answered there. Stop that process and retry."
  exit 1
else
  echo "Starting backend at http://localhost:8000"
  (cd "$BACKEND_DIR" && .venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000) &
  BACKEND_PID=$!
fi

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Frontend already has a listener on port 5173; reusing it."
else
  echo "Starting frontend at http://localhost:5173"
  (cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0) &
  FRONTEND_PID=$!
fi

echo "Open http://localhost:5173 (API docs: http://localhost:8000/docs). Press Ctrl+C to stop services started here."

if [[ -z "$BACKEND_PID" && -z "$FRONTEND_PID" ]]; then
  exit 0
fi
if [[ -n "$BACKEND_PID" && -n "$FRONTEND_PID" ]]; then
  wait "$BACKEND_PID" "$FRONTEND_PID"
elif [[ -n "$BACKEND_PID" ]]; then
  wait "$BACKEND_PID"
else
  wait "$FRONTEND_PID"
fi
