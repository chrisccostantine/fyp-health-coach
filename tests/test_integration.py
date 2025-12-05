import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services.app import app


def test_full_flow():
    client = app.test_client()

    # Plan
    plan_resp = client.post(
        "/plan",
        json={
            "profile": {
                "user_id": "demo-user",
                "age": 28,
                "sex": "M",
                "height_cm": 180,
                "weight_kg": 80,
                "activity_level": "moderate",
                "equipment": ["dumbbells", "outdoor"],
            },
            "goal": {"type": "fat_loss", "deficit_kcal": 400, "target_minutes": 40},
        },
    )
    assert plan_resp.status_code == 200
    plan_json = plan_resp.get_json()
    assert "meals" in plan_json and "workouts" in plan_json

    # Schedule
    schedule_resp = client.post(
        "/schedule",
        json={
            "user_id": "demo-user",
            "windows": ["06:30-07:30", "12:00-13:00", "19:00-20:00"],
            "meals": plan_json["meals"],
            "workouts": plan_json["workouts"],
        },
    )
    assert schedule_resp.status_code == 200
    schedule_json = schedule_resp.get_json()
    assert schedule_json["ok"] is True
    assert len(schedule_json["events"]) >= 1

    # Nudge
    nudge_resp = client.post("/nudge", json={"user_id": "demo-user", "tone": "coach", "goal": "stay_consistent"})
    assert nudge_resp.status_code == 200
    assert "message" in nudge_resp.get_json()

    # Feedback
    first_event = schedule_json["events"][0]
    feedback_resp = client.post(
        "/feedback",
        json={
            "event_id": first_event["id"],
            "user_id": "demo-user",
            "rating": 5,
            "reason": "felt great",
            "bandit_arm": "coach",
        },
    )
    assert feedback_resp.status_code == 200
    assert feedback_resp.get_json()["ok"] is True
