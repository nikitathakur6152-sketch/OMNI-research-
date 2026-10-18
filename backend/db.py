import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "app.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                message TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )"""
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS auth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )"""
        )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hmac.compare_digest(candidate, digest)


def create_user(name: str, email: str, password: str) -> dict:
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash),
        )
        user_id = cursor.lastrowid
    return {"id": user_id, "name": name.strip(), "email": email.strip().lower()}


def get_user_by_email(email: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"], "password_hash": row["password_hash"]}


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
    return token


def record_auth_event(user_id: int, event_type: str) -> None:
    """Keep a server-side audit trail without recording credentials or session tokens."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO auth_events (user_id, event_type) VALUES (?, ?)",
            (user_id, event_type),
        )


def list_auth_events():
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT e.id, e.event_type, e.created_at, u.name, u.email
               FROM auth_events e JOIN users u ON u.id = e.user_id
               ORDER BY e.id DESC LIMIT 500"""
        ).fetchall()
    return [dict(row) for row in rows]


def revoke_session(token: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_user_by_token(token: str):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (token,),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def save_chat(user_id: int, task: str, message: str, answer: str) -> None:
    with get_db_connection() as conn:
        conn.execute("INSERT INTO chat_history (user_id, task, message, answer) VALUES (?, ?, ?, ?)",
                     (user_id, task, message, answer))


def list_chat_history(user_id: int):
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, task, message, answer, created_at FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT 100", (user_id,)).fetchall()
    return [dict(row) for row in rows]
