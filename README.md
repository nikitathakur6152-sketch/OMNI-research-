# OMNI-research-
omni research using agents
# OmniResearch AI

A small research workspace for web search, YouTube transcripts, PDF questions, and code help.

## Requirements

- Python 3.9 or newer
- Node.js 20 or newer
- API keys for the AI features you want to use (see below)

## Run locally

The easiest way to start both services is:

```sh
./start.sh
```

On first run, the script creates the backend virtual environment, installs missing dependencies, creates `backend/.env` from the blank template if needed, and starts both servers. PDF support uses machine learning packages and may take a few minutes to install. Press Ctrl+C to stop services started by the script.

For manual setup, use two terminals:

1. Start the backend:

   ```sh
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   uvicorn app.main:app --reload
   ```

2. In a second terminal, start the frontend:

   ```sh
   cd frontend
   npm ci
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173), create an account, and start chatting. The API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

The frontend proxies API requests to the local backend, so no frontend environment file is needed for local development.

## Configure AI features

Edit `backend/.env` and add the keys for the features you use:

| Feature | Environment variables |
| --- | --- |
| Chat, PDF, YouTube, and code | `MISTRAL_API_KEY` (optional `MISTRAL_MODEL`) |
| Web research | `TAVILY_API_KEY` and `MISTRAL_API_KEY` |

The app and account screens start without API keys. Features that need a missing key will show a clear error when requested. PDF indexing downloads the `all-MiniLM-L6-v2` embedding model the first time a PDF is uploaded.

## Notes

- User accounts and sessions are stored in `backend/app.db`.
- PDF vector data is held in memory and is cleared when the backend restarts; upload PDFs again after a restart.
- Do not commit `.env` files or real API keys.
