from sqlalchemy import create_engine, text
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False)

SCHEMA = '''
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
'''

def init_db():
    with engine.begin() as conn:
        for stmt in SCHEMA.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

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
