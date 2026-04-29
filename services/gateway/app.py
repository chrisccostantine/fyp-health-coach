import os
import uuid

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from services.common.models import DayPlan, Goal, PlanMeal, PlanWorkout, UserProfile
from services.common.storage import (
    create_auth_session,
    create_auth_user,
    delete_auth_session,
    get_auth_session,
    get_auth_user_by_email,
    get_latest_plan,
    get_user,
    init_db,
    save_plan,
    upsert_user,
)

DIET_URL = os.environ.get("DIET_URL", "http://127.0.0.1:8101")
EXERCISE_URL = os.environ.get("EXERCISE_URL", "http://127.0.0.1:8102")
MOTIVATION_URL = os.environ.get("MOTIVATION_URL", "http://127.0.0.1:8103")
SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://127.0.0.1:8104")
FEEDBACK_URL = os.environ.get("FEEDBACK_URL", "http://127.0.0.1:8105")

app = Flask(__name__)
CORS(app)
init_db()


def _serialize_auth_user(user: dict):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user.get("display_name") or "",
    }


def _get_token_from_request():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def _get_current_session():
    token = _get_token_from_request()
    if not token:
        return None
    return get_auth_session(token)


def _require_auth():
    session = _get_current_session()
    if not session:
        return None, (jsonify({"error": "Authentication required"}), 401)
    return session, None


def _sync_calendar_for_plan(user_id: str, plan: dict):
    try:
        res = requests.post(
            f"{SCHEDULER_URL}/calendar/sync",
            json={"user_id": user_id, "plan": plan},
            timeout=20,
        )
        if res.status_code == 200:
            return res.json()
    except requests.RequestException:
        return None
    return None


def _list_calendar(user_id: str):
    try:
        res = requests.get(
            f"{SCHEDULER_URL}/calendar/list",
            params={"user_id": user_id},
            timeout=10,
        )
        if res.status_code == 200:
            return res.json()
    except requests.RequestException:
        return None
    return None


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/")
def home():
    return jsonify({"ok": True, "service": "gateway"})


@app.post("/auth/signup")
def signup():
    data = request.get_json(force=True)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    display_name = str(data.get("display_name", "")).strip() or None

    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if get_auth_user_by_email(email):
        return jsonify({"error": "An account with this email already exists."}), 409

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    password_hash = generate_password_hash(password)
    try:
        create_auth_user(user_id, email, password_hash, display_name)
    except IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 409

    token = create_auth_session(user_id)
    return jsonify(
        {
            "ok": True,
            "token": token,
            "user": {
                "user_id": user_id,
                "email": email,
                "display_name": display_name or "",
            },
        }
    ), 201


@app.post("/auth/login")
def login():
    data = request.get_json(force=True)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = get_auth_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    token = create_auth_session(user["user_id"])
    return jsonify({"ok": True, "token": token, "user": _serialize_auth_user(user)})


@app.get("/auth/me")
def me():
    session, error = _require_auth()
    if error:
        return error
    return jsonify({"ok": True, "user": _serialize_auth_user(session)})


@app.post("/auth/logout")
def logout():
    token = _get_token_from_request()
    if token:
        delete_auth_session(token)
    return jsonify({"ok": True})


@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    text = data.get("text", "").lower()
    if "plan" in text:
        return jsonify(
            {
                "reply": "Sure, let's make today's plan. Call /plan/today with your profile & goal."
            }
        )
    if "nudge" in text or "motivate" in text:
        res = requests.post(
            f"{MOTIVATION_URL}/nudge/send",
            json={
                "user_id": data.get("user_id", "anon"),
                "tone": "coach",
                "goal": "stay_consistent",
            },
        ).json()
        return jsonify({"reply": res["message"]})
    return jsonify(
        {
            "reply": "Hi! I can plan meals/workouts, keep your calendar in sync, and log feedback. Try /plan/today."
        }
    )


@app.post("/plan/today")
def plan_today():
    payload = request.get_json(force=True)
    try:
        session = _get_current_session()
        user_id = session["user_id"] if session else payload.get("user_id", "anon")
        profile = UserProfile(**payload.get("profile", {}))
        goal = Goal(**payload.get("goal", {}))
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    diet_res = requests.post(
        f"{DIET_URL}/diet/suggest",
        json={
            "user_id": user_id,
            "profile": profile.model_dump(),
            "goal": goal.model_dump(),
        },
        timeout=20,
    )
    if diet_res.status_code != 200:
        return jsonify({"error": "diet agent failed", "detail": diet_res.text}), 502
    diet = diet_res.json()

    work_res = requests.post(
        f"{EXERCISE_URL}/exercise/suggest",
        json={
            "user_id": user_id,
            "profile": profile.model_dump(),
            "goal": goal.model_dump(),
            "equipment": payload.get("equipment", []),
        },
        timeout=20,
    )
    if work_res.status_code != 200:
        return jsonify({"error": "exercise agent failed", "detail": work_res.text}), 502
    work = work_res.json()

    plan = DayPlan(
        user_id=user_id,
        meals=[PlanMeal(**m) for m in diet["meals"]],
        workouts=[PlanWorkout(**w) for w in work["workouts"]],
    )
    plan_payload = plan.model_dump()
    save_plan(user_id, plan_payload)
    calendar = _sync_calendar_for_plan(user_id, plan_payload)
    return jsonify({**plan_payload, "calendar": calendar})


@app.post("/diet/chat")
def diet_chat():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id = session["user_id"] if session else body.get("user_id", "anon")
    res = requests.post(f"{DIET_URL}/diet/chat", json=body, timeout=30)
    data = res.json()
    updated_plan = data.get("updated_plan")
    if res.status_code == 200 and isinstance(updated_plan, dict):
        updated_plan["user_id"] = user_id
        save_plan(user_id, updated_plan)
        data["calendar"] = _sync_calendar_for_plan(user_id, updated_plan)
    return jsonify(data), res.status_code


@app.post("/exercise/chat")
def exercise_chat():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id = session["user_id"] if session else body.get("user_id", "anon")
    res = requests.post(f"{EXERCISE_URL}/exercise/chat", json=body, timeout=30)
    data = res.json()
    updated_plan = data.get("updated_plan")
    if res.status_code == 200 and isinstance(updated_plan, dict):
        updated_plan["user_id"] = user_id
        save_plan(user_id, updated_plan)
        data["calendar"] = _sync_calendar_for_plan(user_id, updated_plan)
    return jsonify(data), res.status_code


@app.get("/calendar")
def calendar_list():
    session = _get_current_session()
    requested_user_id = request.args.get("user_id", "anon")
    user_id = session["user_id"] if session else requested_user_id
    data = _list_calendar(user_id)
    if data is None:
        return jsonify({"error": "calendar service unavailable"}), 502
    return jsonify(data)


@app.post("/calendar/sync")
def calendar_sync():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id = session["user_id"] if session else body.get("user_id", "anon")
    plan = body.get("plan")
    if not isinstance(plan, dict):
        plan = get_latest_plan(user_id)
    if not isinstance(plan, dict):
        return jsonify({"error": "No plan available to sync."}), 400

    plan["user_id"] = user_id
    data = _sync_calendar_for_plan(user_id, plan)
    if data is None:
        return jsonify({"error": "calendar service unavailable"}), 502
    return jsonify(data)


@app.post("/nudge/send")
def nudge_send():
    body = request.get_json(force=True)
    res = requests.post(f"{MOTIVATION_URL}/nudge/send", json=body)
    return jsonify(res.json()), res.status_code


@app.get("/user/<user_id>")
def get_user_route(user_id):
    session = _get_current_session()
    if session and session["user_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    data = get_user(user_id)
    if not data:
        return jsonify({"exists": False})
    plan = get_latest_plan(user_id)
    calendar = _list_calendar(user_id)
    return jsonify({"exists": True, **data, "plan": plan, "calendar": calendar})


@app.post("/user/<user_id>/profile")
def save_user_profile(user_id):
    session = _get_current_session()
    if session and session["user_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    body = request.get_json(force=True)
    upsert_user(
        user_id,
        profile=body.get("profile", {}),
        goal=body.get("goal", {}),
        quiz_data=body.get("quiz_data", {}),
    )
    return jsonify({"ok": True})


@app.post("/feedback")
def feedback():
    body = request.get_json(force=True)
    res = requests.post(f"{FEEDBACK_URL}/feedback", json=body)
    return jsonify(res.json()), res.status_code


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
