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
            "health_data_consent": True,
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
            "health_data_consent": True,
        },
    )
    assert first.status_code == 201

    second = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Someone Else",
            "email": "omar@example.com",
            "password": "duplicate123",
            "health_data_consent": True,
        },
    )
    assert second.status_code == 409
    assert "already exists" in second.get_json()["error"]


def test_dietitian_inbox_and_announcement_channel(gateway_client):
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
            "password": "securepass123",
        },
    )
    assert client_res.status_code == 201
    client = client_res.get_json()["client"]

    inbox_res = gateway_client.get(
        "/messages/inbox",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert inbox_res.status_code == 200
    assert inbox_res.get_json()["inbox"][0]["partner"]["user_id"] == client["user_id"]

    channel_res = gateway_client.post(
        "/announcements/channels",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={"name": "Weekly Updates", "client_user_ids": [client["user_id"]]},
    )
    assert channel_res.status_code == 201
    channel_id = channel_res.get_json()["channel"]["id"]

    message_res = gateway_client.post(
        f"/announcements/channels/{channel_id}/messages",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={"body": "Remember to log your meals today."},
    )
    assert message_res.status_code == 200
    assert message_res.get_json()["messages"][0]["body"].startswith("Remember")

    update_channel_res = gateway_client.patch(
        f"/announcements/channels/{channel_id}",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={"name": "Updated Weekly Updates", "client_user_ids": [client["user_id"]]},
    )
    assert update_channel_res.status_code == 200
    assert update_channel_res.get_json()["channel"]["name"] == "Updated Weekly Updates"

    client_login = gateway_client.post(
        "/auth/login",
        json={"email": "client@example.com", "password": "securepass123"},
    )
    client_token = client_login.get_json()["token"]
    client_channel = gateway_client.get(
        f"/announcements/channels/{channel_id}",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert client_channel.status_code == 200
    assert client_channel.get_json()["can_send"] is False

    forbidden_reply = gateway_client.post(
        f"/announcements/channels/{channel_id}/messages",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"body": "Can I reply?"},
    )
    assert forbidden_reply.status_code == 403


def test_private_inbox_unread_count_clears_after_read(gateway_client):
    dietitian_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Dietitian",
            "email": "dietitian2@example.com",
            "password": "securepass123",
            "role": "dietitian",
        },
    )
    dietitian_token = dietitian_res.get_json()["token"]
    client_res = gateway_client.post(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "display_name": "Client",
            "email": "client2@example.com",
            "password": "securepass123",
        },
    )
    client = client_res.get_json()["client"]
    client_login = gateway_client.post(
        "/auth/login",
        json={"email": "client2@example.com", "password": "securepass123"},
    )
    client_token = client_login.get_json()["token"]
    dietitian_id = dietitian_res.get_json()["user"]["user_id"]

    send_res = gateway_client.post(
        f"/messages/{dietitian_id}",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"body": "Hello"},
    )
    assert send_res.status_code == 201

    inbox_res = gateway_client.get(
        "/messages/inbox",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert inbox_res.get_json()["inbox"][0]["unread_count"] == 1

    read_res = gateway_client.post(
        f"/messages/{client['user_id']}/read",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={},
    )
    assert read_res.status_code == 200

    refreshed = gateway_client.get(
        "/messages/inbox",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert refreshed.get_json()["inbox"][0]["unread_count"] == 0


def test_client_updates_are_visible_to_group_and_moderated(gateway_client):
    dietitian_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Dietitian",
            "email": "updates-dietitian@example.com",
            "password": "securepass123",
            "role": "dietitian",
        },
    )
    dietitian_token = dietitian_res.get_json()["token"]

    client_one_res = gateway_client.post(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "display_name": "Client One",
            "email": "updates-client-one@example.com",
            "password": "securepass123",
        },
    )
    client_two_res = gateway_client.post(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "display_name": "Client Two",
            "email": "updates-client-two@example.com",
            "password": "securepass123",
        },
    )
    assert client_one_res.status_code == 201
    assert client_two_res.status_code == 201

    client_one_login = gateway_client.post(
        "/auth/login",
        json={"email": "updates-client-one@example.com", "password": "securepass123"},
    )
    client_two_login = gateway_client.post(
        "/auth/login",
        json={"email": "updates-client-two@example.com", "password": "securepass123"},
    )
    client_one_token = client_one_login.get_json()["token"]
    client_two_token = client_two_login.get_json()["token"]

    image_data = "data:image/png;base64,aGVsbG8="
    create_res = gateway_client.post(
        "/client-updates",
        headers={"Authorization": f"Bearer {client_one_token}"},
        json={"body": "Meal prep went well", "image_data": image_data},
    )
    assert create_res.status_code == 201
    update_id = create_res.get_json()["update"]["id"]

    peer_feed = gateway_client.get(
        "/client-updates",
        headers={"Authorization": f"Bearer {client_two_token}"},
    )
    assert peer_feed.status_code == 200
    assert peer_feed.get_json()["updates"][0]["body"] == "Meal prep went well"

    forbidden_delete = gateway_client.delete(
        f"/client-updates/{update_id}",
        headers={"Authorization": f"Bearer {client_two_token}"},
    )
    assert forbidden_delete.status_code == 403

    dietitian_feed = gateway_client.get(
        "/client-updates",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert dietitian_feed.status_code == 200
    assert dietitian_feed.get_json()["updates"][0]["image_data"] == image_data

    delete_res = gateway_client.delete(
        f"/client-updates/{update_id}",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert delete_res.status_code == 200

    empty_feed = gateway_client.get(
        "/client-updates",
        headers={"Authorization": f"Bearer {client_two_token}"},
    )
    assert empty_feed.get_json()["updates"] == []


def test_signup_requires_health_data_consent_for_user(gateway_client):
    res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "No Consent",
            "email": "noconsent@example.com",
            "password": "securepass123",
            "role": "user",
        },
    )
    assert res.status_code == 400
    assert "consent" in res.get_json()["error"].lower()


def test_expired_session_is_rejected(gateway_client):
    import sys

    storage = sys.modules["services.common.storage"]
    create_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Expired",
            "email": "expired@example.com",
            "password": "securepass123",
            "health_data_consent": True,
        },
    )
    assert create_res.status_code == 201
    user_id = create_res.get_json()["user"]["user_id"]
    expired_token = storage.create_auth_session(user_id, "2000-01-01T00:00:00+00:00")

    res = gateway_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


def test_privacy_export_and_delete_account(gateway_client):
    signup_res = gateway_client.post(
        "/auth/signup",
        json={
            "display_name": "Privacy",
            "email": "privacy@example.com",
            "password": "securepass123",
            "health_data_consent": True,
        },
    )
    assert signup_res.status_code == 201
    token = signup_res.get_json()["token"]

    export_res = gateway_client.get(
        "/privacy/export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert export_res.status_code == 200
    assert export_res.get_json()["export"]["account"]["email"] == "privacy@example.com"

    delete_res = gateway_client.delete(
        "/privacy/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_res.status_code == 200

    me_res = gateway_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 401


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
        if url.endswith("/diet/chat"):
            current_plan = json.get("current_plan", {}) if isinstance(json, dict) else {}
            return DummyResponse(
                {
                    "assistant_reply": "Updated meal timing.",
                    "updated_plan": {
                        "user_id": current_plan.get("user_id", "anon"),
                        "meals": [
                            {
                                "name": "Dietitian Edited Bowl",
                                "calories": 520,
                                "macros": {"protein": 38, "carbs": 45, "fat": 16},
                                "when": "12:30",
                            }
                        ],
                        "workouts": current_plan.get("workouts", []),
                    },
                }
            )
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

    clients_res = gateway_client.get(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert clients_res.status_code == 200
    listed_client = clients_res.get_json()["clients"][0]
    assert listed_client["has_plan"] is True
    assert listed_client["plan_review"]["status"] == "pending_review"
    assert listed_client["adherence_summary"]["status"] == "pending"

    adherence_res = gateway_client.post(
        "/adherence/item",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "user_id": login_res.get_json()["user"]["user_id"],
            "item_key": "2026-05-01:meal:0:breakfast",
            "item_type": "meal",
            "title": "Breakfast",
            "status": "ate",
            "plan_date": "2026-05-01",
        },
    )
    assert adherence_res.status_code == 200
    assert adherence_res.get_json()["summary"]["meal_adherence"] == 100

    dietitian_adherence_res = gateway_client.get(
        f"/adherence?user_id={login_res.get_json()['user']['user_id']}",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert dietitian_adherence_res.status_code == 200
    assert dietitian_adherence_res.get_json()["items"][0]["status"] == "ate"

    clients_after_adherence = gateway_client.get(
        "/dietitian/clients",
        headers={"Authorization": f"Bearer {dietitian_token}"},
    )
    assert clients_after_adherence.status_code == 200
    assert clients_after_adherence.get_json()["clients"][0]["adherence_summary"]["status"] == "on_track"

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

    diet_chat_res = gateway_client.post(
        "/diet/chat",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "user_id": login_res.get_json()["user"]["user_id"],
            "message": "Move lunch earlier",
            "current_plan": plan,
        },
    )
    assert diet_chat_res.status_code == 200
    edited_plan = diet_chat_res.get_json()["updated_plan"]
    assert edited_plan["meals"][0]["name"] == "Dietitian Edited Bowl"
    assert edited_plan["review"]["status"] == "pending_review"
    assert edited_plan["review"]["last_edited_by_role"] == "dietitian"

    reject_res = gateway_client.post(
        "/plan/review",
        headers={"Authorization": f"Bearer {dietitian_token}"},
        json={
            "client_user_id": login_res.get_json()["user"]["user_id"],
            "status": "rejected",
            "note": "Needs a safer version.",
        },
    )
    assert reject_res.status_code == 200
    assert reject_res.get_json()["review"]["status"] == "rejected"
