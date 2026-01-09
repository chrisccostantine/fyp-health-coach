# FYP Health Coach — Multi‑Agent Flask System (MVP)

This is a **modular multi‑agent personal health coach** with a Flask **Gateway** that orchestrates five agents:
**Diet, Exercise, Motivation, Scheduler, Feedback**. It’s an MVP aligned with your FYP brief and ready to run locally.

> Python 3.10+ recommended.

## Quick start (local, no Docker)

```bash
# 1) Create a virtual environment
python -m venv .venv && source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2) Install requirements for all services
pip install -r services/requirements.all.txt

# 3) Start the agents in separate terminals (or run the helper script)
# Terminal A
python services/diet_agent/app.py
# Terminal B
python services/exercise_agent/app.py
# Terminal C
python services/motivation_agent/app.py
# Terminal D
python services/scheduler_agent/app.py
# Terminal E
python services/feedback_agent/app.py
# Terminal F (Gateway)
python services/gateway/app.py

# (Optional) seed demo data
python scripts/seed.py

# (Optional) Run a demo flow that exercises the APIs end-to-end
python scripts/demo_flow.py
```

Gateway runs on **http://127.0.0.1:8000**. Each agent runs on its own port (see below).

## Services & Ports

- Gateway (Flask): **:8000**
- Diet Agent: **:8101**
- Exercise Agent: **:8102**
- Motivation Agent: **:8103**
- Scheduler Agent: **:8104**
- Feedback Agent: **:8105**

## API (Gateway)

- `POST /chat` — echo-style chat + quick intent routing (MVP).
- `POST /plan/today` — generate a daily plan (meals + workouts) from Diet/Exercise.
- `POST /schedule/commit` — schedule events (delegates to Scheduler).
- `POST /nudge/send` — send a motivation nudge (returns text; you can wire push later).
- `POST /feedback` — log feedback and update simple bandit policy via Feedback Agent.

### Example request: `POST /plan/today`
```json
{
  "user_id": "demo-user",
  "profile": {"age": 24, "sex": "M", "height_cm": 178, "weight_kg": 78, "activity_level": "moderate",
              "diet": {"type": "balanced", "calorie_target": null}},
  "goal": {"type": "fat_loss", "deficit_kcal": 400},
  "equipment": ["dumbbells", "pullup_bar"]
}
```

## Storage

- SQLite file at `storage/app.db` via a minimal helper.
- You can later swap to Firebase/Firestore by replacing the storage adapter in `services/common/storage.py`.

## Tests

- `pytest` integration test: `tests/test_integration.py` spins up against running services.
- Lightweight and fast.

## Next steps (hooks present in code)

- Swap the storage adapter to Firebase.
- Add Google Calendar to `scheduler_agent` (stubs and TODOs in code).
- Replace rule-based suggestions with learned policies (Feedback Agent includes a simple epsilon‑greedy bandit).

---

© You. Built by ChatGPT as a scaffold you can extend.
