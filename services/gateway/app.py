from flask import Flask, request, jsonify
import requests, os
from pydantic import ValidationError
from services.common.models import UserProfile, Goal, DayPlan, PlanMeal, PlanWorkout
from services.common.storage import init_db
from flask_cors import CORS

DIET_URL = os.environ.get("DIET_URL", "http://127.0.0.1:8101")
EXERCISE_URL = os.environ.get("EXERCISE_URL", "http://127.0.0.1:8102")
MOTIVATION_URL = os.environ.get("MOTIVATION_URL", "http://127.0.0.1:8103")
SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://127.0.0.1:8104")
FEEDBACK_URL = os.environ.get("FEEDBACK_URL", "http://127.0.0.1:8105")

app = Flask(__name__)
CORS(app)
init_db()

# ✅ ADD THESE HERE (BEFORE app.run)
@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.get("/")
def home():
    return jsonify({"ok": True, "service": "gateway"})

@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    text = data.get("text","").lower()
    if "plan" in text:
        return jsonify({"reply": "Sure, let's make today's plan. Call /plan/today with your profile & goal."})
    elif "nudge" in text or "motivate" in text:
        res = requests.post(f"{MOTIVATION_URL}/nudge/send", json={"user_id": data.get("user_id","anon"), "tone": "coach", "goal":"stay_consistent"}).json()
        return jsonify({"reply": res["message"]})
    return jsonify({"reply": "Hi! I can plan meals/workouts, schedule, and log feedback. Try /plan/today."})

@app.post("/plan/today")
def plan_today():
    payload = request.get_json(force=True)
    try:
        user_id = payload.get("user_id","anon")
        profile = UserProfile(**payload.get("profile",{}))
        goal = Goal(**payload.get("goal",{}))
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    diet_res = requests.post(
        f"{DIET_URL}/diet/suggest",
        json={"user_id": user_id, "profile": profile.model_dump(), "goal": goal.model_dump()},
        timeout=20,
    )
    if diet_res.status_code != 200:
        return jsonify({"error": "diet agent failed", "detail": diet_res.text}), 502
    diet = diet_res.json()

    work_res = requests.post(
        f"{EXERCISE_URL}/exercise/suggest",
        json={"user_id": user_id, "profile": profile.model_dump(), "goal": goal.model_dump(), "equipment": payload.get("equipment", [])},
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
    return jsonify(plan.model_dump())


@app.post("/diet/chat")
def diet_chat():
    body = request.get_json(force=True)
    res = requests.post(f"{DIET_URL}/diet/chat", json=body, timeout=30)
    return jsonify(res.json()), res.status_code

@app.post("/schedule/commit")
def schedule_commit():
    body = request.get_json(force=True)
    res = requests.post(f"{SCHEDULER_URL}/schedule/commit", json=body)
    return jsonify(res.json()), res.status_code

@app.post("/nudge/send")
def nudge_send():
    body = request.get_json(force=True)
    res = requests.post(f"{MOTIVATION_URL}/nudge/send", json=body)
    return jsonify(res.json()), res.status_code

@app.post("/feedback")
def feedback():
    body = request.get_json(force=True)
    res = requests.post(f"{FEEDBACK_URL}/feedback", json=body)
    return jsonify(res.json()), res.status_code

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
