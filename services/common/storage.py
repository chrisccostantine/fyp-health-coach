import json
import os
import secrets
from pathlib import Path

from sqlalchemy import create_engine, text


def _database_url() -> str:
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if raw_url:
        if raw_url.startswith("postgres://"):
            return "postgresql+psycopg2://" + raw_url[len("postgres://") :]
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return raw_url

    db_path = Path(
        os.environ.get(
            "STORAGE_DB_PATH",
            Path(__file__).resolve().parents[2] / "storage" / "app.db",
        )
    )
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = _database_url()
IS_POSTGRES = DATABASE_URL.startswith("postgresql+")
engine = create_engine(DATABASE_URL, future=True, echo=False, pool_pre_ping=True)

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    user_id TEXT,
    rating INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bandit_arm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT,
    arm TEXT,
    pulls INTEGER DEFAULT 0,
    reward_sum REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    profile TEXT,
    goal TEXT,
    quiz_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_key TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    status TEXT,
    notes TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user',
    managed_by_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS google_calendar_tokens (
    user_id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    token_type TEXT,
    scope TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS google_oauth_states (
    state TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

SCHEMA_POSTGRES = '''
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    event_id TEXT,
    user_id TEXT,
    rating INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bandit_arm (
    id SERIAL PRIMARY KEY,
    agent TEXT,
    arm TEXT,
    pulls INTEGER DEFAULT 0,
    reward_sum REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    profile TEXT,
    goal TEXT,
    quiz_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_plans (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_key TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    status TEXT,
    notes TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user',
    managed_by_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS google_calendar_tokens (
    user_id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    token_type TEXT,
    scope TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS google_oauth_states (
    state TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

SCHEMA = SCHEMA_POSTGRES if IS_POSTGRES else SCHEMA_SQLITE

MIGRATIONS = [
    "ALTER TABLE auth_users ADD COLUMN role TEXT DEFAULT 'user'",
    "ALTER TABLE auth_users ADD COLUMN managed_by_user_id TEXT",
]

def init_db():
    with engine.begin() as conn:
        for stmt in SCHEMA.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
        for stmt in MIGRATIONS:
            try:
                conn.execute(text(stmt))
            except Exception:
                # Column already exists or backend does not need this migration.
                pass

def record_feedback(event_id:str, user_id:str, rating:int, reason:str|None):
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO feedback(event_id,user_id,rating,reason)
                             VALUES (:e,:u,:r,:re)"""),
                     {"e":event_id,"u":user_id,"r":rating,"re":reason})

def get_arms(agent:str):
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, agent, arm, pulls, reward_sum FROM bandit_arm WHERE agent=:a"), {"a":agent}).mappings().all()
    return [dict(r) for r in rows]

def upsert_arm(agent:str, arm:str, reward:float|None=None, pulled:bool=False):
    # Ensure row exists
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO bandit_arm(agent, arm, pulls, reward_sum)
                           SELECT :agent, :arm, 0, 0.0
                           WHERE NOT EXISTS (SELECT 1 FROM bandit_arm WHERE agent=:agent AND arm=:arm)"""),
                     {"agent":agent,"arm":arm})
        if pulled or reward is not None:
            conn.execute(text("""UPDATE bandit_arm SET
                                pulls = pulls + :p,
                                reward_sum = reward_sum + :r
                                WHERE agent=:agent AND arm=:arm"""),
                         {"p":1 if pulled else 0, "r":(reward or 0.0), "agent":agent, "arm":arm})

def upsert_user(user_id: str, profile: dict, goal: dict, quiz_data: dict = None):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO users(user_id, profile, goal, quiz_data, updated_at)
            VALUES(:uid, :p, :g, :q, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                profile=excluded.profile,
                goal=excluded.goal,
                quiz_data=excluded.quiz_data,
                updated_at=CURRENT_TIMESTAMP
        """), {
            "uid": user_id,
            "p": json.dumps(profile or {}),
            "g": json.dumps(goal or {}),
            "q": json.dumps(quiz_data or {}),
        })

def get_user(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT profile, goal, quiz_data FROM users WHERE user_id=:uid"),
            {"uid": user_id}
        ).mappings().first()
    if not row:
        return None
    return {
        "profile": json.loads(row["profile"] or "{}"),
        "goal": json.loads(row["goal"] or "{}"),
        "quiz_data": json.loads(row["quiz_data"] or "{}"),
    }

def save_plan(user_id: str, plan: dict):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO user_plans(user_id, plan) VALUES(:uid, :p)"),
            {"uid": user_id, "p": json.dumps(plan or {})}
        )

def get_latest_plan(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT plan FROM user_plans WHERE user_id=:uid ORDER BY created_at DESC LIMIT 1"),
            {"uid": user_id}
        ).mappings().first()
    if not row:
        return None
    return json.loads(row["plan"])

def replace_calendar_events(user_id: str, events: list[dict]):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM calendar_events WHERE user_id = :uid"),
            {"uid": user_id},
        )
        for event in events:
            conn.execute(
                text("""
                    INSERT INTO calendar_events(
                        id, user_id, source_key, type, title, starts_at, ends_at,
                        status, notes, payload, updated_at
                    ) VALUES(
                        :id, :uid, :source_key, :type, :title, :starts_at, :ends_at,
                        :status, :notes, :payload, CURRENT_TIMESTAMP
                    )
                """),
                {
                    "id": event["id"],
                    "uid": user_id,
                    "source_key": event["source_key"],
                    "type": event["type"],
                    "title": event["title"],
                    "starts_at": event["starts_at"],
                    "ends_at": event.get("ends_at"),
                    "status": event.get("status"),
                    "notes": event.get("notes"),
                    "payload": json.dumps(event.get("payload") or {}),
                },
            )

def get_calendar_events(user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, user_id, source_key, type, title, starts_at, ends_at,
                       status, notes, payload
                FROM calendar_events
                WHERE user_id = :uid
                ORDER BY starts_at ASC, created_at ASC
            """),
            {"uid": user_id},
        ).mappings().all()
    events = []
    for row in rows:
        event = dict(row)
        event["payload"] = json.loads(event.get("payload") or "{}")
        events.append(event)
    return events

def create_auth_user(
    user_id: str,
    email: str,
    password_hash: str,
    display_name: str | None = None,
    role: str = "user",
    managed_by_user_id: str | None = None,
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO auth_users(
                    user_id, email, password_hash, display_name, role, managed_by_user_id, updated_at
                )
                VALUES(
                    :uid, :email, :password_hash, :display_name, :role, :managed_by_user_id, CURRENT_TIMESTAMP
                )
            """),
            {
                "uid": user_id,
                "email": email,
                "password_hash": password_hash,
                "display_name": display_name,
                "role": role,
                "managed_by_user_id": managed_by_user_id,
            },
        )

def get_auth_user_by_email(email: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT user_id, email, password_hash, display_name, role, managed_by_user_id, created_at
                FROM auth_users
                WHERE lower(email) = lower(:email)
            """),
            {"email": email},
        ).mappings().first()
    return dict(row) if row else None

def get_auth_user_by_id(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT user_id, email, password_hash, display_name, role, managed_by_user_id, created_at
                FROM auth_users
                WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).mappings().first()
    return dict(row) if row else None

def list_managed_auth_users(manager_user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT user_id, email, display_name, role, managed_by_user_id, created_at
                FROM auth_users
                WHERE managed_by_user_id = :uid
                ORDER BY created_at ASC, email ASC
            """),
            {"uid": manager_user_id},
        ).mappings().all()
    return [dict(row) for row in rows]

def is_managed_by(manager_user_id: str, client_user_id: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT 1
                FROM auth_users
                WHERE user_id = :client_uid
                  AND managed_by_user_id = :manager_uid
                LIMIT 1
            """),
            {"client_uid": client_user_id, "manager_uid": manager_user_id},
        ).first()
    return bool(row)

def remove_managed_auth_user(manager_user_id: str, client_user_id: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE auth_users
                SET managed_by_user_id = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :client_uid
                  AND managed_by_user_id = :manager_uid
            """),
            {"client_uid": client_user_id, "manager_uid": manager_user_id},
        )
    return result.rowcount > 0

def create_auth_session(user_id: str):
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO auth_sessions(token, user_id) VALUES(:token, :uid)"),
            {"token": token, "uid": user_id},
        )
    return token

def get_auth_session(token: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT s.token, s.user_id, u.email, u.display_name, u.role, u.managed_by_user_id
                FROM auth_sessions s
                JOIN auth_users u ON u.user_id = s.user_id
                WHERE s.token = :token
            """),
            {"token": token},
        ).mappings().first()
    return dict(row) if row else None

def delete_auth_session(token: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM auth_sessions WHERE token = :token"),
            {"token": token},
        )

def upsert_google_calendar_token(user_id: str, token_data: dict):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO google_calendar_tokens(
                    user_id, access_token, refresh_token, token_type, scope, expires_at, updated_at
                ) VALUES(
                    :uid, :access_token, :refresh_token, :token_type, :scope, :expires_at, CURRENT_TIMESTAMP
                )
                ON CONFLICT(user_id) DO UPDATE SET
                    access_token=excluded.access_token,
                    refresh_token=COALESCE(excluded.refresh_token, google_calendar_tokens.refresh_token),
                    token_type=excluded.token_type,
                    scope=excluded.scope,
                    expires_at=excluded.expires_at,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {
                "uid": user_id,
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_type": token_data.get("token_type"),
                "scope": token_data.get("scope"),
                "expires_at": token_data.get("expires_at"),
            },
        )

def get_google_calendar_token(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT user_id, access_token, refresh_token, token_type, scope, expires_at
                FROM google_calendar_tokens
                WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).mappings().first()
    return dict(row) if row else None

def delete_google_calendar_token(user_id: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM google_calendar_tokens WHERE user_id = :uid"),
            {"uid": user_id},
        )

def create_google_oauth_state(user_id: str):
    state = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO google_oauth_states(state, user_id) VALUES(:state, :uid)"),
            {"state": state, "uid": user_id},
        )
    return state

def consume_google_oauth_state(state: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT state, user_id FROM google_oauth_states WHERE state = :state"),
            {"state": state},
        ).mappings().first()
        if row:
            conn.execute(
                text("DELETE FROM google_oauth_states WHERE state = :state"),
                {"state": state},
            )
    return dict(row) if row else None
