import os
from dotenv import load_dotenv
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
DEVELOPER_EMAILS = {email.strip().lower() for email in os.getenv("DEVELOPER_EMAILS", "").split(",") if email.strip()}
