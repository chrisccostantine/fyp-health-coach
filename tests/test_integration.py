import requests, time

BASE = "http://127.0.0.1"
PORTS = {"gateway":8000, "diet":8101, "exercise":8102, "motivation":8103, "scheduler":8104, "feedback":8105}

def url(svc, path):
    return f"{BASE}:{PORTS[svc]}{path}"

def test_flow():
    # Plan
    plan = requests.post(url("gateway","/plan/today"), json={
        "user_id":"demo-user",
        "profile":{"age":24,"sex":"M","height_cm":178,"weight_kg":78,"activity_level":"moderate"},
        "goal":{"type":"fat_loss","deficit_kcal":400},
        "equipment":["dumbbells"]
    }).json()
    assert "meals" in plan and "workouts" in plan

    # Schedule
    ev = []
    for m in plan["meals"]:
        ev.append({"type":"meal","name":m["name"],"scheduled_at":"2025-10-16T08:00:00","duration_min":15})
    for w in plan["workouts"]:
        ev.append({"type":"workout","name":w["name"],"scheduled_at":"2025-10-16T18:00:00","duration_min":w["duration_min"]})
    sch = requests.post(url("gateway","/schedule/commit"), json={"user_id":"demo-user","events":ev}).json()
    assert sch["ok"]

    # Nudge
    ndg = requests.post(url("gateway","/nudge/send"), json={"user_id":"demo-user","tone":"coach","goal":"stay_consistent"}).json()
    assert "message" in ndg

    # Feedback
    first_event_id = sch["events"][0]["id"]
    fb = requests.post(url("gateway","/feedback"), json={"event_id": first_event_id, "user_id":"demo-user", "rating":5, "reason":"felt great", "bandit_arm":"coach"}).json()
    assert fb["ok"]
