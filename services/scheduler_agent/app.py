import os
import uuid
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from services.common.storage import get_calendar_events, init_db, replace_calendar_events

app = Flask(__name__)
init_db()

DEFAULT_MEAL_TIMES = ["08:00", "13:00", "19:00"]
DEFAULT_WORKOUT_TIME = "18:00"


def _today_iso_date():
    return datetime.now().date().isoformat()


def _to_iso_datetime(value: str | None, fallback_time: str) -> str:
    if not value:
        return f"{_today_iso_date()}T{fallback_time}:00"

    raw = str(value).strip()
    if len(raw) == 5 and raw[2] == ":":
        return f"{_today_iso_date()}T{raw}:00"

    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.replace(microsecond=0).isoformat()
    except ValueError:
        return f"{_today_iso_date()}T{fallback_time}:00"


def _build_event(source_key: str, item_type: str, title: str, starts_at: str, duration_min: int, payload: dict):
    start_dt = datetime.fromisoformat(starts_at)
    ends_at = (start_dt + timedelta(minutes=duration_min)).replace(microsecond=0).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "source_key": source_key,
        "type": item_type,
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "status": "planned",
        "notes": payload.get("notes") or "",
        "payload": payload,
    }


def _calendar_from_plan(user_id: str, plan: dict):
    meals = plan.get("meals", []) or []
    workouts = plan.get("workouts", []) or []
    events = []

    for idx, meal in enumerate(meals):
        starts_at = _to_iso_datetime(
            meal.get("when") or meal.get("time"),
            DEFAULT_MEAL_TIMES[idx % len(DEFAULT_MEAL_TIMES)],
        )
        events.append(
            _build_event(
                source_key=f"meal:{idx}",
                item_type="meal",
                title=meal.get("name") or meal.get("title") or f"Meal {idx + 1}",
                starts_at=starts_at,
                duration_min=30,
                payload={
                    "calories": meal.get("calories", meal.get("kcal")),
                    "macros": meal.get("macros", {}),
                },
            )
        )

    for idx, workout in enumerate(workouts):
        duration = int(workout.get("duration_min", workout.get("duration", 30)) or 30)
        starts_at = _to_iso_datetime(
            workout.get("when") or workout.get("time"),
            DEFAULT_WORKOUT_TIME,
        )
        events.append(
            _build_event(
                source_key=f"workout:{idx}",
                item_type="workout",
                title=workout.get("name") or workout.get("title") or f"Workout {idx + 1}",
                starts_at=starts_at,
                duration_min=duration,
                payload={
                    "duration_min": duration,
                    "intensity": workout.get("intensity"),
                },
            )
        )

    replace_calendar_events(user_id, events)
    return events


@app.post("/calendar/sync")
def sync_calendar():
    body = request.get_json(force=True)
    user_id = body.get("user_id", "anon")
    plan = body.get("plan", {})
    events = _calendar_from_plan(user_id, plan)
    return jsonify(
        {
            "ok": True,
            "message": "Calendar synced from the latest plan.",
            "events": events,
        }
    )


@app.get("/calendar/list")
def list_calendar():
    user_id = request.args.get("user_id") or "anon"
    return jsonify({"ok": True, "events": get_calendar_events(user_id)})


if __name__ == "__main__":
    host = os.environ.get("SCHEDULER_HOST", "127.0.0.1")
    port = int(os.environ.get("SCHEDULER_PORT", "8104"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
