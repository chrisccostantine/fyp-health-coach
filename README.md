# Intelligent Personal Health Coach (reboot)

Fresh restart of the multi‑agent health coach inspired by the project brief. Everything now runs from a minimal standard‑library HTTP server (`services/app.py`) with modular agents for diet, exercise, motivation, scheduling, and feedback.

## Stack
- Python 3.11 (standard library only)
- SQLite storage for bandit + feedback

## Getting started
```bash
python -m services.app  # launches http://127.0.0.1:8000
```

## API
- `POST /plan` — Build a daily plan with meals + workouts from profile and goal.
- `POST /schedule` — Turn a plan into scheduled events using optional time windows.
- `POST /nudge` — Send a motivation nudge (multi‑armed bandit chooses tone).
- `POST /feedback` — Log ratings and reinforce the bandit arm used.

### Example: generate a plan
```bash
curl -X POST http://127.0.0.1:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
        "profile": {"user_id": "demo", "age": 28, "height_cm": 180, "weight_kg": 80, "activity_level": "moderate", "equipment": ["dumbbells", "outdoor"]},
        "goal": {"type": "fat_loss", "deficit_kcal": 400, "target_minutes": 40}
      }'
```

### Example: schedule and nudge
```bash
curl -X POST http://127.0.0.1:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{
        "user_id": "demo",
        "windows": ["06:30-07:30", "12:00-13:00", "19:00-20:00"],
        "meals": [],
        "workouts": []
      }'

curl -X POST http://127.0.0.1:8000/nudge \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo", "tone": "coach", "goal": "stay_consistent"}'
```

## Tests
```bash
pytest
```

## Notes
- Agents live under `services/agents/` and are plain Python modules.
- Bandit rewards are stored in `storage/app.db` and updated whenever feedback specifies `bandit_arm`.
- The system is intentionally rule‑based so it’s easy to extend with LLM calls or ML models later.
