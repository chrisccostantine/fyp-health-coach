import importlib
import sys

import pytest


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
