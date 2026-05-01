import importlib
import sys

import pytest


class DummyResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


@pytest.fixture()
def gateway_client(monkeypatch, tmp_path):
    db_path = tmp_path / "test-auth.db"
    monkeypatch.setenv("STORAGE_DB_PATH", str(db_path))

    for module_name in ["services.common.storage", "services.gateway.app"]:
        if module_name in sys.modules:
            del sys.modules[module_name]

    storage = importlib.import_module("services.common.storage")
    importlib.reload(storage)
    gateway_module = importlib.import_module("services.gateway.app")
    gateway_module = importlib.reload(gateway_module)

    gateway_module.app.config["TESTING"] = True
    return gateway_module.app.test_client()


def test_signup_login_and_logout_flow(gateway_client):
    signup_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Amina",
            "email": "amina@example.com",
            "password": "securepass123",
        },
    )
    assert signup_res.status_code == 201
    signup_data = signup_res.get_json()
    assert signup_data["ok"] is True
    assert signup_data["user"]["email"] == "amina@example.com"
    assert signup_data["user"]["display_name"] == "Amina"
    assert signup_data["token"]

    token = signup_data["token"]
    me_res = gateway_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["user_id"] == signup_data["user"]["user_id"]

    logout_res = gateway_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert logout_res.status_code == 200

    expired_res = gateway_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expired_res.status_code == 401

    login_res = gateway_client.post(
        "/auth/login",
        json={"email": "amina@example.com", "password": "securepass123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.get_json()
    assert login_data["user"]["email"] == "amina@example.com"
    assert login_data["token"] != token


def test_signup_rejects_duplicate_email(gateway_client):
    first = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Omar",
            "email": "omar@example.com",
            "password": "duplicate123",
        },
    )
    assert first.status_code == 201

    second = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Someone Else",
            "email": "omar@example.com",
            "password": "duplicate123",
        },
    )
    assert second.status_code == 409
    assert "already exists" in second.get_json()["error"]


def test_plan_today_blocks_unsafe_minor_profile(gateway_client):
    res = gateway_client.post(
        "/plan/today",
        json={
            "user_id": "demo-user",
            "profile": {
                "age": 15,
                "sex": "M",
                "height_cm": 170,
                "weight_kg": 65,
                "activity_level": "moderate",
            },
            "goal": {"type": "general_health", "deficit_kcal": 0},
            "equipment": [],
        },
    )

    assert res.status_code == 422
    data = res.get_json()
    assert data["safety"]["blocked"] is True
    assert "under 16" in data["safety"]["blocks"][0]


def test_progress_checkin_and_weekly_update(gateway_client):
    profile_res = gateway_client.post(
        "/user/demo-user/profile",
        json={
            "profile": {"age": 30, "height_cm": 178, "weight_kg": 82, "activity_level": "light"},
            "goal": {"type": "fat_loss", "deficit_kcal": 400},
            "quiz_data": {},
        },
    )
    assert profile_res.status_code == 200

    checkin_res = gateway_client.post(
        "/progress/check-in",
        json={
            "user_id": "demo-user",
            "weight_kg": 82,
            "meal_adherence": 55,
            "workout_adherence": 50,
            "energy_level": 2,
            "notes": "hungry and tired",
            "checked_in_on": "2026-05-01",
        },
    )
    assert checkin_res.status_code == 201
    assert checkin_res.get_json()["checkins"][0]["meal_adherence"] == 55
    assert checkin_res.get_json()["weekly_lock"]["locked"] is True

    duplicate_checkin_res = gateway_client.post(
        "/progress/check-in",
        json={
            "user_id": "demo-user",
            "weight_kg": 81.7,
            "meal_adherence": 75,
            "workout_adherence": 70,
            "energy_level": 3,
            "checked_in_on": "2026-05-03",
        },
    )
    assert duplicate_checkin_res.status_code == 409
    assert duplicate_checkin_res.get_json()["weekly_lock"]["locked"] is True

    weekly_res = gateway_client.post(
        "/progress/weekly-update",
        json={"user_id": "demo-user"},
    )
    assert weekly_res.status_code == 200
    weekly = weekly_res.get_json()["weekly_update"]
    assert weekly["adjustments"]["calorie_adjustment_kcal"] > 0
    assert weekly["adjustments"]["workout_adjustment"] in {"reduce_intensity", "reduce_duration"}

    progress_res = gateway_client.get("/progress?user_id=demo-user")
    assert progress_res.status_code == 200
    progress = progress_res.get_json()
    assert len(progress["checkins"]) == 1
    assert progress["weekly_update"]["summary"]


def test_managed_client_plan_requires_dietitian_review(gateway_client, monkeypatch):
    import sys

    gateway_module = sys.modules["services.gateway.app"]

    def fake_post(url, json=None, timeout=None, **kwargs):
        if url.endswith("/diet/suggest"):
            return DummyResponse(
                {
                    "meals": [
                        {
                            "name": "Managed Client Bowl",
                            "calories": 500,
                            "macros": {"protein": 35, "carbs": 45, "fat": 15},
                            "when": "13:00",
                        }
                    ]
                }
            )
        if url.endswith("/exercise/suggest"):
            return DummyResponse(
                {
                    "workouts": [
                        {
                            "name": "Managed Client Walk",
                            "duration_min": 25,
                            "intensity": "low",
                            "when": "18:00",
                        }
                    ]
                }
            )
        if url.endswith("/calendar/sync"):
            return DummyResponse({"ok": True, "events": []})
        return DummyResponse({"ok": True})

    monkeypatch.setattr(gateway_module.requests, "post", fake_post)

    dietitian_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Dietitian",
            "email": "dietitian@example.com",
            "password": "securepass123",
            "role": "dietitian",
        },
    )
    assert dietitian_res.status_code == 201
    dietitian_token = dietitian_res.get_json()["token"]

    client_res = gateway_client.post(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "display_name": "Client",
            "email": "client@example.com",
            "password": "clientpass123",
        },
    )
    assert client_res.status_code == 201

    login_res = gateway_client.post(
        "/auth/login",
        json={"email": "client@example.com", "password": "clientpass123"},
    )
    assert login_res.status_code == 200
    client_token = login_res.get_json()["token"]

    plan_res = gateway_client.post(
        "/plan/today",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "user_id": login_res.get_json()["user"]["user_id"],
            "profile": {
                "age": 30,
                "sex": "F",
                "height_cm": 165,
                "weight_kg": 62,
                "activity_level": "moderate",
            },
            "goal": {"type": "general_health", "deficit_kcal": 0},
            "equipment": [],
        },
    )
    assert plan_res.status_code == 200
    plan = plan_res.get_json()
    assert plan["review"]["required"] is True
    assert plan["review"]["status"] == "pending_review"

    review_res = gateway_client.post(
        "/plan/review",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "client_user_id": login_res.get_json()["user"]["user_id"],
            "status": "approved",
            "note": "Looks appropriate for this week.",
        },
    )
    assert review_res.status_code == 200
    review = review_res.get_json()["review"]
    assert review["status"] == "approved"
    assert review["note"] == "Looks appropriate for this week."
