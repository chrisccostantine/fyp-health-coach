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
    health_data_consent INTEGER DEFAULT 0,
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
CREATE TABLE IF NOT EXISTS auth_password_resets (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_nudge_settings (
    user_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    tone TEXT DEFAULT 'coach',
    goal_text TEXT DEFAULT 'stay_consistent',
    send_time TEXT DEFAULT '08:00',
    timezone TEXT DEFAULT 'UTC',
    last_sent_on TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_user_id TEXT NOT NULL,
    recipient_user_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS private_message_reads (
    user_id TEXT NOT NULL,
    partner_user_id TEXT NOT NULL,
    last_read_message_id INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, partner_user_id)
);
CREATE TABLE IF NOT EXISTS announcement_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dietitian_user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS announcement_channel_recipients (
    channel_id INTEGER NOT NULL,
    client_user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(channel_id, client_user_id)
);
CREATE TABLE IF NOT EXISTS announcement_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    sender_user_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS client_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    dietitian_user_id TEXT NOT NULL,
    body TEXT,
    image_data TEXT,
    expires_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS progress_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    weight_kg REAL,
    meal_adherence INTEGER,
    workout_adherence INTEGER,
    energy_level INTEGER,
    notes TEXT,
    checked_in_on TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS item_adherence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    item_key TEXT NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL,
    plan_date TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_key)
);
CREATE TABLE IF NOT EXISTS weekly_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id TEXT,
    target_user_id TEXT,
    action TEXT NOT NULL,
    metadata TEXT,
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
    health_data_consent INTEGER DEFAULT 0,
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
CREATE TABLE IF NOT EXISTS auth_password_resets (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_nudge_settings (
    user_id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    tone TEXT DEFAULT 'coach',
    goal_text TEXT DEFAULT 'stay_consistent',
    send_time TEXT DEFAULT '08:00',
    timezone TEXT DEFAULT 'UTC',
    last_sent_on TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS private_messages (
    id SERIAL PRIMARY KEY,
    sender_user_id TEXT NOT NULL,
    recipient_user_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS private_message_reads (
    user_id TEXT NOT NULL,
    partner_user_id TEXT NOT NULL,
    last_read_message_id INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, partner_user_id)
);
CREATE TABLE IF NOT EXISTS announcement_channels (
    id SERIAL PRIMARY KEY,
    dietitian_user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS announcement_channel_recipients (
    channel_id INTEGER NOT NULL,
    client_user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(channel_id, client_user_id)
);
CREATE TABLE IF NOT EXISTS announcement_messages (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    sender_user_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS client_updates (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    dietitian_user_id TEXT NOT NULL,
    body TEXT,
    image_data TEXT,
    expires_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS progress_checkins (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    weight_kg REAL,
    meal_adherence INTEGER,
    workout_adherence INTEGER,
    energy_level INTEGER,
    notes TEXT,
    checked_in_on TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS item_adherence (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    item_key TEXT NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL,
    plan_date TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_key)
);
CREATE TABLE IF NOT EXISTS weekly_updates (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor_user_id TEXT,
    target_user_id TEXT,
    action TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

SCHEMA = SCHEMA_POSTGRES if IS_POSTGRES else SCHEMA_SQLITE

MIGRATIONS = [
    "ALTER TABLE auth_users ADD COLUMN role TEXT DEFAULT 'user'",
    "ALTER TABLE auth_users ADD COLUMN managed_by_user_id TEXT",
    "ALTER TABLE auth_users ADD COLUMN health_data_consent INTEGER DEFAULT 0",
    "CREATE TABLE IF NOT EXISTS auth_password_resets (token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS user_nudge_settings (user_id TEXT PRIMARY KEY)",
    "ALTER TABLE user_nudge_settings ADD COLUMN enabled INTEGER DEFAULT 0",
    "ALTER TABLE user_nudge_settings ADD COLUMN tone TEXT DEFAULT 'coach'",
    "ALTER TABLE user_nudge_settings ADD COLUMN goal_text TEXT DEFAULT 'stay_consistent'",
    "ALTER TABLE user_nudge_settings ADD COLUMN send_time TEXT DEFAULT '08:00'",
    "ALTER TABLE user_nudge_settings ADD COLUMN timezone TEXT DEFAULT 'UTC'",
    "ALTER TABLE user_nudge_settings ADD COLUMN last_sent_on TEXT",
    "ALTER TABLE user_nudge_settings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE user_nudge_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "CREATE TABLE IF NOT EXISTS private_messages (id SERIAL PRIMARY KEY, sender_user_id TEXT NOT NULL, recipient_user_id TEXT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS private_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_user_id TEXT NOT NULL, recipient_user_id TEXT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS private_message_reads (user_id TEXT NOT NULL, partner_user_id TEXT NOT NULL, last_read_message_id INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, partner_user_id))",
    "CREATE TABLE IF NOT EXISTS announcement_channels (id SERIAL PRIMARY KEY, dietitian_user_id TEXT NOT NULL, name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS announcement_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, dietitian_user_id TEXT NOT NULL, name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS announcement_channel_recipients (channel_id INTEGER NOT NULL, client_user_id TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(channel_id, client_user_id))",
    "CREATE TABLE IF NOT EXISTS announcement_messages (id SERIAL PRIMARY KEY, channel_id INTEGER NOT NULL, sender_user_id TEXT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS announcement_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id INTEGER NOT NULL, sender_user_id TEXT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS client_updates (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, dietitian_user_id TEXT NOT NULL, body TEXT, image_data TEXT, expires_at TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS client_updates (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, dietitian_user_id TEXT NOT NULL, body TEXT, image_data TEXT, expires_at TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS progress_checkins (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, weight_kg REAL, meal_adherence INTEGER, workout_adherence INTEGER, energy_level INTEGER, notes TEXT, checked_in_on TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS progress_checkins (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, weight_kg REAL, meal_adherence INTEGER, workout_adherence INTEGER, energy_level INTEGER, notes TEXT, checked_in_on TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS item_adherence (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, item_key TEXT NOT NULL, item_type TEXT NOT NULL, title TEXT, status TEXT NOT NULL, plan_date TEXT, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, item_key))" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS item_adherence (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, item_key TEXT NOT NULL, item_type TEXT NOT NULL, title TEXT, status TEXT NOT NULL, plan_date TEXT, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, item_key))",
    "CREATE TABLE IF NOT EXISTS weekly_updates (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, recommendation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS weekly_updates (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, recommendation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, actor_user_id TEXT, target_user_id TEXT, action TEXT NOT NULL, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" if IS_POSTGRES else "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id TEXT, target_user_id TEXT, action TEXT NOT NULL, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
]

def init_db():
    for stmt in SCHEMA.strip().split(';'):
        s = stmt.strip()
        if not s:
            continue
        with engine.begin() as conn:
            conn.execute(text(s))

    for stmt in MIGRATIONS:
        try:
            with engine.begin() as conn:
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
    health_data_consent: bool = False,
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO auth_users(
                    user_id, email, password_hash, display_name, role, managed_by_user_id,
                    health_data_consent, updated_at
                )
                VALUES(
                    :uid, :email, :password_hash, :display_name, :role, :managed_by_user_id,
                    :health_data_consent, CURRENT_TIMESTAMP
                )
            """),
            {
                "uid": user_id,
                "email": email,
                "password_hash": password_hash,
                "display_name": display_name,
                "role": role,
                "managed_by_user_id": managed_by_user_id,
                "health_data_consent": 1 if health_data_consent else 0,
            },
        )

def get_auth_user_by_email(email: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT user_id, email, password_hash, display_name, role, managed_by_user_id,
                       health_data_consent, created_at
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
                SELECT user_id, email, password_hash, display_name, role, managed_by_user_id,
                       health_data_consent, created_at
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
                SELECT user_id, email, display_name, role, managed_by_user_id,
                       health_data_consent, created_at
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


def create_private_message(sender_user_id: str, recipient_user_id: str, body: str):
    message_body = str(body or "").strip()
    if not message_body:
        raise ValueError("Message body is required.")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO private_messages(sender_user_id, recipient_user_id, body)
                VALUES (:sender_user_id, :recipient_user_id, :body)
                """
            ),
            {
                "sender_user_id": sender_user_id,
                "recipient_user_id": recipient_user_id,
                "body": message_body,
            },
        )


def list_private_messages(user_a_id: str, user_b_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, sender_user_id, recipient_user_id, body, created_at
                FROM private_messages
                WHERE (sender_user_id = :user_a AND recipient_user_id = :user_b)
                   OR (sender_user_id = :user_b AND recipient_user_id = :user_a)
                ORDER BY created_at ASC, id ASC
                """
            ),
            {
                "user_a": user_a_id,
                "user_b": user_b_id,
            },
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def mark_private_messages_read(user_id: str, partner_user_id: str):
    with engine.begin() as conn:
        latest_id = conn.execute(
            text(
                """
                SELECT MAX(id)
                FROM private_messages
                WHERE (sender_user_id = :user_id AND recipient_user_id = :partner_id)
                   OR (sender_user_id = :partner_id AND recipient_user_id = :user_id)
                """
            ),
            {"user_id": user_id, "partner_id": partner_user_id},
        ).scalar() or 0
        if IS_POSTGRES:
            conn.execute(
                text(
                    """
                    INSERT INTO private_message_reads(user_id, partner_user_id, last_read_message_id, updated_at)
                    VALUES (:user_id, :partner_id, :latest_id, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, partner_user_id)
                    DO UPDATE SET last_read_message_id = EXCLUDED.last_read_message_id,
                                  updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {"user_id": user_id, "partner_id": partner_user_id, "latest_id": latest_id},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO private_message_reads(user_id, partner_user_id, last_read_message_id, updated_at)
                    VALUES (:user_id, :partner_id, :latest_id, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, partner_user_id)
                    DO UPDATE SET last_read_message_id = excluded.last_read_message_id,
                                  updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {"user_id": user_id, "partner_id": partner_user_id, "latest_id": latest_id},
            )


def list_private_inbox(user_id: str, partners: list[dict]):
    inbox = []
    with engine.begin() as conn:
        for partner in partners:
            partner_id = partner.get("user_id")
            if not partner_id:
                continue
            row = conn.execute(
                text(
                    """
                    SELECT id, sender_user_id, recipient_user_id, body, created_at
                    FROM private_messages
                    WHERE (sender_user_id = :user_id AND recipient_user_id = :partner_id)
                       OR (sender_user_id = :partner_id AND recipient_user_id = :user_id)
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "partner_id": partner_id},
            ).mappings().first()
            unread_count = conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM private_messages m
                    LEFT JOIN private_message_reads r
                      ON r.user_id = :user_id
                     AND r.partner_user_id = :partner_id
                    WHERE m.sender_user_id = :partner_id
                      AND m.recipient_user_id = :user_id
                      AND m.id > COALESCE(r.last_read_message_id, 0)
                    """
                ),
                {"user_id": user_id, "partner_id": partner_id},
            ).scalar() or 0
            inbox.append(
                {
                    "partner": partner,
                    "last_message": dict(row) if row else None,
                    "unread_count": int(unread_count),
                }
            )
    return sorted(
        inbox,
        key=lambda item: str((item.get("last_message") or {}).get("created_at") or ""),
        reverse=True,
    )


def create_announcement_channel(dietitian_user_id: str, name: str, client_user_ids: list[str]):
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Channel name is required.")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO announcement_channels(dietitian_user_id, name)
                VALUES (:dietitian_user_id, :name)
                """
            ),
            {"dietitian_user_id": dietitian_user_id, "name": clean_name},
        )
        channel_id = conn.execute(
            text(
                """
                SELECT MAX(id)
                FROM announcement_channels
                WHERE dietitian_user_id = :dietitian_user_id
                """
            ),
            {"dietitian_user_id": dietitian_user_id},
        ).scalar()
        for client_user_id in client_user_ids:
            conn.execute(
                text(
                    """
                    INSERT INTO announcement_channel_recipients(channel_id, client_user_id)
                    VALUES (:channel_id, :client_user_id)
                    """
                ),
                {"channel_id": channel_id, "client_user_id": client_user_id},
            )
    return get_announcement_channel(channel_id)


def update_announcement_channel(channel_id: int, name: str, client_user_ids: list[str]):
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Channel name is required.")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE announcement_channels
                SET name = :name
                WHERE id = :channel_id
                """
            ),
            {"channel_id": channel_id, "name": clean_name},
        )
        conn.execute(
            text("DELETE FROM announcement_channel_recipients WHERE channel_id = :channel_id"),
            {"channel_id": channel_id},
        )
        for client_user_id in client_user_ids:
            conn.execute(
                text(
                    """
                    INSERT INTO announcement_channel_recipients(channel_id, client_user_id)
                    VALUES (:channel_id, :client_user_id)
                    """
                ),
                {"channel_id": channel_id, "client_user_id": client_user_id},
            )
    return get_announcement_channel(channel_id)


def get_announcement_channel(channel_id: int):
    with engine.begin() as conn:
        channel = conn.execute(
            text(
                """
                SELECT id, dietitian_user_id, name, created_at
                FROM announcement_channels
                WHERE id = :channel_id
                """
            ),
            {"channel_id": channel_id},
        ).mappings().first()
        if not channel:
            return None
        recipients = conn.execute(
            text(
                """
                SELECT client_user_id
                FROM announcement_channel_recipients
                WHERE channel_id = :channel_id
                ORDER BY client_user_id ASC
                """
            ),
            {"channel_id": channel_id},
        ).mappings().all()
    result = dict(channel)
    result["client_user_ids"] = [row["client_user_id"] for row in recipients]
    return result


def list_announcement_channels_for_dietitian(dietitian_user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id, c.dietitian_user_id, c.name, c.created_at,
                       COUNT(r.client_user_id) AS recipient_count,
                       MAX(m.created_at) AS last_message_at
                FROM announcement_channels c
                LEFT JOIN announcement_channel_recipients r ON r.channel_id = c.id
                LEFT JOIN announcement_messages m ON m.channel_id = c.id
                WHERE c.dietitian_user_id = :dietitian_user_id
                GROUP BY c.id, c.dietitian_user_id, c.name, c.created_at
                ORDER BY COALESCE(MAX(m.created_at), c.created_at) DESC
                """
            ),
            {"dietitian_user_id": dietitian_user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def list_announcement_channels_for_client(client_user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id, c.dietitian_user_id, c.name, c.created_at,
                       MAX(m.created_at) AS last_message_at
                FROM announcement_channels c
                JOIN announcement_channel_recipients r ON r.channel_id = c.id
                LEFT JOIN announcement_messages m ON m.channel_id = c.id
                WHERE r.client_user_id = :client_user_id
                GROUP BY c.id, c.dietitian_user_id, c.name, c.created_at
                ORDER BY COALESCE(MAX(m.created_at), c.created_at) DESC
                """
            ),
            {"client_user_id": client_user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def create_announcement_message(channel_id: int, sender_user_id: str, body: str):
    message_body = str(body or "").strip()
    if not message_body:
        raise ValueError("Announcement body is required.")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO announcement_messages(channel_id, sender_user_id, body)
                VALUES (:channel_id, :sender_user_id, :body)
                """
            ),
            {"channel_id": channel_id, "sender_user_id": sender_user_id, "body": message_body},
        )


def list_announcement_messages(channel_id: int):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, channel_id, sender_user_id, body, created_at
                FROM announcement_messages
                WHERE channel_id = :channel_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"channel_id": channel_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def create_client_update(
    user_id: str,
    dietitian_user_id: str,
    body: str | None,
    image_data: str | None,
    expires_at: str,
):
    clean_body = str(body or "").strip()
    clean_image = str(image_data or "").strip()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO client_updates(user_id, dietitian_user_id, body, image_data, expires_at)
                VALUES (:user_id, :dietitian_user_id, :body, :image_data, :expires_at)
                """
            ),
            {
                "user_id": user_id,
                "dietitian_user_id": dietitian_user_id,
                "body": clean_body or None,
                "image_data": clean_image or None,
                "expires_at": expires_at,
            },
        )
        update_id = conn.execute(
            text(
                """
                SELECT MAX(id)
                FROM client_updates
                WHERE user_id = :user_id AND dietitian_user_id = :dietitian_user_id
                """
            ),
            {"user_id": user_id, "dietitian_user_id": dietitian_user_id},
        ).scalar()
    return get_client_update(update_id)


def get_client_update(update_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT u.id, u.user_id, u.dietitian_user_id, u.body, u.image_data,
                       u.expires_at, u.created_at, a.email, a.display_name
                FROM client_updates u
                LEFT JOIN auth_users a ON a.user_id = u.user_id
                WHERE u.id = :update_id
                """
            ),
            {"update_id": update_id},
        ).mappings().first()
    return dict(row) if row else None


def list_client_updates_for_group(dietitian_user_id: str, now_iso: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT u.id, u.user_id, u.dietitian_user_id, u.body, u.image_data,
                       u.expires_at, u.created_at, a.email, a.display_name
                FROM client_updates u
                LEFT JOIN auth_users a ON a.user_id = u.user_id
                WHERE u.dietitian_user_id = :dietitian_user_id
                  AND u.expires_at > :now_iso
                ORDER BY u.created_at DESC, u.id DESC
                """
            ),
            {"dietitian_user_id": dietitian_user_id, "now_iso": now_iso},
        ).mappings().all()
    return [dict(row) for row in rows]


def delete_client_update(update_id: int):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM client_updates WHERE id = :update_id"),
            {"update_id": update_id},
        )
    return result.rowcount > 0


def create_auth_session(user_id: str, expires_at: str | None = None):
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO auth_sessions(token, user_id, expires_at) VALUES(:token, :uid, :expires_at)"),
            {"token": token, "uid": user_id, "expires_at": expires_at},
        )
    return token

def get_auth_session(token: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT s.token, s.user_id, s.expires_at, u.email, u.display_name, u.role,
                       u.managed_by_user_id, u.health_data_consent
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

def delete_auth_sessions_for_user(user_id: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM auth_sessions WHERE user_id = :uid"),
            {"uid": user_id},
        )

def update_auth_user_password(user_id: str, password_hash: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE auth_users
                SET password_hash = :password_hash,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :uid
            """),
            {"uid": user_id, "password_hash": password_hash},
        )

def create_password_reset_token(user_id: str, expires_at: str):
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM auth_password_resets WHERE user_id = :uid"),
            {"uid": user_id},
        )
        conn.execute(
            text("""
                INSERT INTO auth_password_resets(token, user_id, expires_at)
                VALUES(:token, :uid, :expires_at)
            """),
            {"token": token, "uid": user_id, "expires_at": expires_at},
        )
    return token

def get_password_reset_token(token: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT token, user_id, expires_at, created_at
                FROM auth_password_resets
                WHERE token = :token
            """),
            {"token": token},
        ).mappings().first()
    return dict(row) if row else None

def delete_password_reset_token(token: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM auth_password_resets WHERE token = :token"),
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

def upsert_nudge_settings(
    user_id: str,
    *,
    enabled: bool,
    tone: str,
    goal_text: str,
    send_time: str,
    timezone: str,
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO user_nudge_settings(
                    user_id, enabled, tone, goal_text, send_time, timezone, updated_at
                ) VALUES(
                    :uid, :enabled, :tone, :goal_text, :send_time, :timezone, CURRENT_TIMESTAMP
                )
                ON CONFLICT(user_id) DO UPDATE SET
                    enabled=excluded.enabled,
                    tone=excluded.tone,
                    goal_text=excluded.goal_text,
                    send_time=excluded.send_time,
                    timezone=excluded.timezone,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {
                "uid": user_id,
                "enabled": 1 if enabled else 0,
                "tone": tone,
                "goal_text": goal_text,
                "send_time": send_time,
                "timezone": timezone,
            },
        )

def get_nudge_settings(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT user_id, enabled, tone, goal_text, send_time, timezone, last_sent_on
                FROM user_nudge_settings
                WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).mappings().first()
    if not row:
        return None
    payload = dict(row)
    payload["enabled"] = bool(payload.get("enabled"))
    return payload

def list_all_nudge_settings():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT user_id, enabled, tone, goal_text, send_time, timezone, last_sent_on
                FROM user_nudge_settings
                WHERE enabled = 1
                ORDER BY updated_at ASC, user_id ASC
            """)
        ).mappings().all()
    payloads = []
    for row in rows:
        payload = dict(row)
        payload["enabled"] = bool(payload.get("enabled"))
        payloads.append(payload)
    return payloads

def mark_nudge_sent(user_id: str, sent_on: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE user_nudge_settings
                SET last_sent_on = :sent_on,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :uid
            """),
            {"uid": user_id, "sent_on": sent_on},
        )


def record_progress_checkin(
    user_id: str,
    *,
    weight_kg: float | None,
    meal_adherence: int | None,
    workout_adherence: int | None,
    energy_level: int | None,
    notes: str | None,
    checked_in_on: str,
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO progress_checkins(
                    user_id, weight_kg, meal_adherence, workout_adherence,
                    energy_level, notes, checked_in_on
                ) VALUES(
                    :uid, :weight_kg, :meal_adherence, :workout_adherence,
                    :energy_level, :notes, :checked_in_on
                )
            """),
            {
                "uid": user_id,
                "weight_kg": weight_kg,
                "meal_adherence": meal_adherence,
                "workout_adherence": workout_adherence,
                "energy_level": energy_level,
                "notes": notes,
                "checked_in_on": checked_in_on,
            },
        )


def list_progress_checkins(user_id: str, limit: int = 12):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, user_id, weight_kg, meal_adherence, workout_adherence,
                       energy_level, notes, checked_in_on, created_at
                FROM progress_checkins
                WHERE user_id = :uid
                ORDER BY checked_in_on DESC, id DESC
                LIMIT :limit
            """),
            {"uid": user_id, "limit": max(1, int(limit or 12))},
        ).mappings().all()
    return [dict(row) for row in rows]


def record_item_adherence(
    user_id: str,
    item_key: str,
    item_type: str,
    title: str | None,
    status: str,
    plan_date: str | None = None,
    note: str | None = None,
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO item_adherence(
                    user_id, item_key, item_type, title, status, plan_date, note, updated_at
                )
                VALUES(
                    :uid, :item_key, :item_type, :title, :status, :plan_date, :note,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT(user_id, item_key) DO UPDATE SET
                    item_type=excluded.item_type,
                    title=excluded.title,
                    status=excluded.status,
                    plan_date=excluded.plan_date,
                    note=excluded.note,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {
                "uid": user_id,
                "item_key": item_key,
                "item_type": item_type,
                "title": title,
                "status": status,
                "plan_date": plan_date,
                "note": note,
            },
        )


def list_item_adherence(user_id: str, limit: int = 250):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, user_id, item_key, item_type, title, status, plan_date,
                       note, created_at, updated_at
                FROM item_adherence
                WHERE user_id = :uid
                ORDER BY COALESCE(plan_date, '') DESC, updated_at DESC, id DESC
                LIMIT :limit
            """),
            {"uid": user_id, "limit": limit},
        ).mappings().all()
    return [dict(row) for row in rows]


def item_adherence_summary(user_id: str):
    rows = list_item_adherence(user_id, limit=500)
    meal_rows = [row for row in rows if row.get("item_type") == "meal"]
    workout_rows = [row for row in rows if row.get("item_type") == "workout"]

    def _rate(items, positive_status):
        if not items:
            return None
        return round(100 * len([row for row in items if row.get("status") == positive_status]) / len(items))

    meal_rate = _rate(meal_rows, "ate")
    workout_rate = _rate(workout_rows, "done")
    rates = [rate for rate in [meal_rate, workout_rate] if rate is not None]
    overall_rate = round(sum(rates) / len(rates)) if rates else None
    if overall_rate is None:
        on_track = "pending"
    elif overall_rate >= 75:
        on_track = "on_track"
    elif overall_rate >= 50:
        on_track = "watch"
    else:
        on_track = "off_track"

    return {
        "meal_logged": len(meal_rows),
        "workout_logged": len(workout_rows),
        "meal_adherence": meal_rate,
        "workout_adherence": workout_rate,
        "overall_adherence": overall_rate,
        "missed_meals": len([row for row in meal_rows if row.get("status") == "missed"]),
        "missed_workouts": len([row for row in workout_rows if row.get("status") == "missed"]),
        "status": on_track,
        "latest": rows[:6],
    }


def save_weekly_update(user_id: str, recommendation: dict):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO weekly_updates(user_id, recommendation)
                VALUES(:uid, :recommendation)
            """),
            {"uid": user_id, "recommendation": json.dumps(recommendation or {})},
        )


def get_latest_weekly_update(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT id, user_id, recommendation, created_at
                FROM weekly_updates
                WHERE user_id = :uid
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """),
            {"uid": user_id},
        ).mappings().first()
    if not row:
        return None
    payload = dict(row)
    payload["recommendation"] = json.loads(payload.get("recommendation") or "{}")
    return payload


def record_audit_log(actor_user_id: str | None, target_user_id: str | None, action: str, metadata: dict | None = None):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO audit_logs(actor_user_id, target_user_id, action, metadata)
                VALUES(:actor_user_id, :target_user_id, :action, :metadata)
            """),
            {
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "action": action,
                "metadata": json.dumps(metadata or {}),
            },
        )


def list_audit_logs_for_user(user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, actor_user_id, target_user_id, action, metadata, created_at
                FROM audit_logs
                WHERE actor_user_id = :uid OR target_user_id = :uid
                ORDER BY created_at DESC, id DESC
            """),
            {"uid": user_id},
        ).mappings().all()
    logs = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.get("metadata") or "{}")
        logs.append(item)
    return logs


def export_user_data(user_id: str):
    with engine.begin() as conn:
        auth_user = conn.execute(
            text("""
                SELECT user_id, email, display_name, role, managed_by_user_id,
                       health_data_consent, created_at
                FROM auth_users WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).mappings().first()
        user = conn.execute(text("SELECT profile, goal, quiz_data, created_at, updated_at FROM users WHERE user_id=:uid"), {"uid": user_id}).mappings().first()
        plans = conn.execute(text("SELECT plan, created_at FROM user_plans WHERE user_id=:uid ORDER BY created_at DESC"), {"uid": user_id}).mappings().all()
        feedback_rows = conn.execute(text("SELECT event_id, rating, reason, created_at FROM feedback WHERE user_id=:uid ORDER BY created_at DESC"), {"uid": user_id}).mappings().all()
        adherence_rows = conn.execute(
            text("""
                SELECT item_key, item_type, title, status, plan_date, note, created_at, updated_at
                FROM item_adherence
                WHERE user_id=:uid
                ORDER BY updated_at DESC
            """),
            {"uid": user_id},
        ).mappings().all()
        messages = conn.execute(
            text("""
                SELECT sender_user_id, recipient_user_id, body, created_at
                FROM private_messages
                WHERE sender_user_id=:uid OR recipient_user_id=:uid
                ORDER BY created_at DESC
            """),
            {"uid": user_id},
        ).mappings().all()
        client_updates = conn.execute(
            text("""
                SELECT user_id, dietitian_user_id, body, image_data, expires_at, created_at
                FROM client_updates
                WHERE user_id=:uid
                ORDER BY created_at DESC
            """),
            {"uid": user_id},
        ).mappings().all()

    return {
        "account": dict(auth_user) if auth_user else None,
        "profile": {
            **dict(user),
            "profile": json.loads(user["profile"] or "{}"),
            "goal": json.loads(user["goal"] or "{}"),
            "quiz_data": json.loads(user["quiz_data"] or "{}"),
        } if user else None,
        "plans": [{"plan": json.loads(row["plan"] or "{}"), "created_at": row["created_at"]} for row in plans],
        "calendar_events": get_calendar_events(user_id),
        "feedback": [dict(row) for row in feedback_rows],
        "item_adherence": [dict(row) for row in adherence_rows],
        "progress_checkins": list_progress_checkins(user_id, limit=1000),
        "weekly_update": get_latest_weekly_update(user_id),
        "nudge_settings": get_nudge_settings(user_id),
        "private_messages": [dict(row) for row in messages],
        "client_updates": [dict(row) for row in client_updates],
        "audit_logs": list_audit_logs_for_user(user_id),
    }


def delete_user_account_data(user_id: str):
    with engine.begin() as conn:
        for stmt in [
            "DELETE FROM feedback WHERE user_id = :uid",
            "DELETE FROM item_adherence WHERE user_id = :uid",
            "DELETE FROM users WHERE user_id = :uid",
            "DELETE FROM user_plans WHERE user_id = :uid",
            "DELETE FROM calendar_events WHERE user_id = :uid",
            "DELETE FROM auth_sessions WHERE user_id = :uid",
            "DELETE FROM google_calendar_tokens WHERE user_id = :uid",
            "DELETE FROM google_oauth_states WHERE user_id = :uid",
            "DELETE FROM auth_password_resets WHERE user_id = :uid",
            "DELETE FROM user_nudge_settings WHERE user_id = :uid",
            "DELETE FROM progress_checkins WHERE user_id = :uid",
            "DELETE FROM weekly_updates WHERE user_id = :uid",
            "DELETE FROM private_messages WHERE sender_user_id = :uid OR recipient_user_id = :uid",
            "DELETE FROM client_updates WHERE user_id = :uid OR dietitian_user_id = :uid",
            "DELETE FROM audit_logs WHERE actor_user_id = :uid OR target_user_id = :uid",
            "UPDATE auth_users SET managed_by_user_id = NULL WHERE managed_by_user_id = :uid",
            "DELETE FROM auth_users WHERE user_id = :uid",
        ]:
            conn.execute(text(stmt), {"uid": user_id})
