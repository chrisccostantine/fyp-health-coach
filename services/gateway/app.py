import os
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from services.common.models import DayPlan, Goal, PlanMeal, PlanWorkout, UserProfile
from services.common.storage import (
    create_auth_session,
    create_auth_user,
    create_google_oauth_state,
    delete_google_calendar_token,
    delete_auth_session,
    get_google_calendar_token,
    get_auth_session,
    get_auth_user_by_email,
    is_managed_by,
    get_latest_plan,
    list_managed_auth_users,
    get_user,
    init_db,
    save_plan,
    upsert_google_calendar_token,
    upsert_user,
    consume_google_oauth_state,
)

DIET_URL = os.environ.get("DIET_URL", "http://127.0.0.1:8101")
EXERCISE_URL = os.environ.get("EXERCISE_URL", "http://127.0.0.1:8102")
MOTIVATION_URL = os.environ.get("MOTIVATION_URL", "http://127.0.0.1:8103")
SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://127.0.0.1:8104")
FEEDBACK_URL = os.environ.get("FEEDBACK_URL", "http://127.0.0.1:8105")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip()
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "UTC")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"

app = Flask(__name__)
CORS(app)
init_db()


def _serialize_auth_user(user: dict):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user.get("display_name") or "",
        "role": user.get("role") or "user",
        "managed_by_user_id": user.get("managed_by_user_id"),
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


def _require_dietitian(session: dict):
    if (session.get("role") or "user") != "dietitian":
        return jsonify({"error": "Dietitian account required"}), 403
    return None


def _resolve_target_user_id(session: dict | None, requested_user_id: str | None):
    if not session:
        return requested_user_id or "anon"

    own_user_id = session["user_id"]
    target_user_id = (requested_user_id or own_user_id or "").strip() or own_user_id
    if target_user_id == own_user_id:
        return target_user_id

    if (session.get("role") or "user") == "dietitian" and is_managed_by(own_user_id, target_user_id):
        return target_user_id

    return None


def _google_calendar_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI and FRONTEND_URL)


def _frontend_redirect(status: str) -> str:
    base = FRONTEND_URL.rstrip("/") if FRONTEND_URL else "/"
    return f"{base}?google_calendar={status}"


def _google_auth_url_for_user(user_id: str) -> str:
    state = create_google_oauth_state(user_id)
    query = urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "include_granted_scopes": "true",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def _token_expiry(expires_in) -> str | None:
    try:
        seconds = int(expires_in or 0)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _google_token_payload(payload: dict, existing: dict | None = None) -> dict:
    existing = existing or {}
    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token") or existing.get("refresh_token"),
        "token_type": payload.get("token_type") or existing.get("token_type"),
        "scope": payload.get("scope") or existing.get("scope"),
        "expires_at": _token_expiry(payload.get("expires_in")),
    }


def _google_access_token_for_user(user_id: str) -> str | None:
    token = get_google_calendar_token(user_id)
    if not token:
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        try:
            if isinstance(expires_at, datetime):
                expiry = expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
            else:
                expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expiry > datetime.now(timezone.utc) + timedelta(seconds=60):
                return token.get("access_token")
        except ValueError:
            pass

    refresh_token = token.get("refresh_token")
    if not refresh_token or not _google_calendar_enabled():
        return token.get("access_token")

    res = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if res.status_code != 200:
        return token.get("access_token")

    refreshed = _google_token_payload(res.json(), existing=token)
    upsert_google_calendar_token(user_id, refreshed)
    return refreshed.get("access_token")


def _google_calendar_sync_status(user_id: str):
    token = get_google_calendar_token(user_id)
    return {
        "enabled": _google_calendar_enabled(),
        "connected": bool(token and token.get("refresh_token")),
    }


def _google_headers(user_id: str):
    access_token = _google_access_token_for_user(user_id)
    if not access_token:
        return None
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _google_error_payload(prefix: str, response=None, detail: str | None = None, debug: str | None = None):
    message = prefix
    if detail:
        message = f"{prefix}: {detail}"
    elif response is not None:
        try:
            payload = response.json()
            detail = (
                payload.get("error_description")
                or payload.get("error", {}).get("message")
                or payload.get("error")
            )
        except ValueError:
            detail = response.text.strip() or response.reason
        if detail:
            message = f"{prefix}: {detail}"
    payload = {"connected": False, "error": message}
    if debug:
        payload["debug"] = debug
    return payload


def _google_event_body(user_id: str, event: dict):
    payload = event.get("payload") or {}
    description_parts = []
    if payload.get("calories") is not None:
        description_parts.append(f"Calories: {payload['calories']}")
    if payload.get("duration_min") is not None:
        description_parts.append(f"Duration: {payload['duration_min']} min")
    if payload.get("intensity"):
        description_parts.append(f"Intensity: {payload['intensity']}")
    if payload.get("macros"):
        macros = payload["macros"]
        description_parts.append(
            "Macros: "
            f"P {macros.get('protein', 0)}g | "
            f"C {macros.get('carbs', 0)}g | "
            f"F {macros.get('fat', 0)}g"
        )
    notes = event.get("notes")
    if notes:
        description_parts.append(str(notes))

    starts_at = event.get("starts_at")
    ends_at = event.get("ends_at") or starts_at
    return {
        "summary": event.get("title") or "Health Coach Event",
        "description": "\n".join(
            [
                part
                for part in [
                    f"Synced from Health Coach ({event.get('type', 'event')}).",
                    *description_parts,
                ]
                if part
            ]
        ),
        "start": {"dateTime": starts_at, "timeZone": APP_TIMEZONE},
        "end": {"dateTime": ends_at, "timeZone": APP_TIMEZONE},
        "extendedProperties": {
            "private": {
                "healthCoachUserId": user_id,
                "healthCoachSourceKey": event.get("source_key", ""),
            }
        },
    }


def _sync_google_calendar_for_user(user_id: str, events: list[dict]):
    try:
        headers = _google_headers(user_id)
        if not headers:
            return None

        res = requests.get(
            GOOGLE_CALENDAR_EVENTS_URL,
            headers=headers,
            params={
                "privateExtendedProperty": f"healthCoachUserId={user_id}",
                "singleEvents": "true",
                "maxResults": 250,
            },
            timeout=20,
        )
        if res.status_code != 200:
            return _google_error_payload("Google Calendar list failed", response=res)

        for item in res.json().get("items", []):
            event_id = item.get("id")
            if event_id:
                delete_res = requests.delete(
                    f"{GOOGLE_CALENDAR_EVENTS_URL}/{event_id}",
                    headers=headers,
                    timeout=20,
                )
                if delete_res.status_code not in {200, 204}:
                    return _google_error_payload(
                        "Google Calendar cleanup failed",
                        response=delete_res,
                    )

        created = []
        for idx, event in enumerate(events):
            try:
                google_event = _google_event_body(user_id, event)
            except Exception as exc:
                return _google_error_payload(
                    f"Google Calendar event build failed for event {idx + 1}",
                    detail=str(exc),
                    debug=traceback.format_exc(limit=3),
                )

            insert_res = requests.post(
                GOOGLE_CALENDAR_EVENTS_URL,
                headers=headers,
                json=google_event,
                timeout=20,
            )
            if insert_res.status_code not in {200, 201}:
                return _google_error_payload(
                    f"Google Calendar event creation failed for event {idx + 1}",
                    response=insert_res,
                )
            created.append(insert_res.json().get("id"))
        return {"connected": True, "created": len(created)}
    except requests.RequestException as exc:
        app.logger.exception("Google Calendar sync request failed for user %s", user_id)
        return _google_error_payload(
            "Google Calendar sync request failed",
            detail=str(exc),
            debug=traceback.format_exc(limit=3),
        )
    except Exception as exc:
        app.logger.exception("Unexpected Google Calendar sync failure for user %s", user_id)
        return _google_error_payload(
            "Google Calendar sync failed",
            detail=str(exc),
            debug=traceback.format_exc(limit=5),
        )


def _sync_calendar_for_plan(user_id: str, plan: dict):
    try:
        res = requests.post(
            f"{SCHEDULER_URL}/calendar/sync",
            json={"user_id": user_id, "plan": plan},
            timeout=20,
        )
        if res.status_code == 200:
            data = res.json()
            google = _sync_google_calendar_for_user(user_id, data.get("events", []))
            if google is not None:
                data["google_calendar"] = google
            return data
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


@app.post("/google/calendar/connect")
def google_calendar_connect():
    session, error = _require_auth()
    if error:
        return error
    if not _google_calendar_enabled():
        return jsonify({"error": "Google Calendar is not configured."}), 503
    return jsonify({"ok": True, "auth_url": _google_auth_url_for_user(session["user_id"])})


@app.get("/google/calendar/status")
def google_calendar_status():
    session, error = _require_auth()
    if error:
        return error
    return jsonify(_google_calendar_sync_status(session["user_id"]))


@app.post("/google/calendar/disconnect")
def google_calendar_disconnect():
    session, error = _require_auth()
    if error:
        return error
    delete_google_calendar_token(session["user_id"])
    return jsonify({"ok": True, "connected": False})


@app.get("/auth/google/callback")
def google_oauth_callback():
    if not _google_calendar_enabled():
        return redirect(_frontend_redirect("not_configured"))

    code = request.args.get("code", "").strip()
    state = request.args.get("state", "").strip()
    if not code or not state:
        return redirect(_frontend_redirect("missing_code"))

    oauth_state = consume_google_oauth_state(state)
    if not oauth_state:
        return redirect(_frontend_redirect("invalid_state"))

    token_res = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    if token_res.status_code != 200:
        return redirect(_frontend_redirect("token_error"))

    user_id = oauth_state["user_id"]
    upsert_google_calendar_token(user_id, _google_token_payload(token_res.json()))
    plan = get_latest_plan(user_id)
    if isinstance(plan, dict):
        _sync_calendar_for_plan(user_id, plan)
    return redirect(_frontend_redirect("connected"))


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
    role = str(data.get("role", "user")).strip().lower() or "user"

    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if role not in {"user", "dietitian"}:
        return jsonify({"error": "Role must be 'user' or 'dietitian'."}), 400
    if get_auth_user_by_email(email):
        return jsonify({"error": "An account with this email already exists."}), 409

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    password_hash = generate_password_hash(password)
    try:
        create_auth_user(user_id, email, password_hash, display_name, role=role)
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
                "role": role,
                "managed_by_user_id": None,
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


@app.get("/dietitian/clients")
def dietitian_clients():
    session, error = _require_auth()
    if error:
        return error
    role_error = _require_dietitian(session)
    if role_error:
        return role_error
    clients = list_managed_auth_users(session["user_id"])
    return jsonify({"ok": True, "clients": [_serialize_auth_user(client) for client in clients]})


@app.post("/dietitian/clients")
def dietitian_create_client():
    session, error = _require_auth()
    if error:
        return error
    role_error = _require_dietitian(session)
    if role_error:
        return role_error

    data = request.get_json(force=True)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    display_name = str(data.get("display_name", "")).strip() or None

    if not email or "@" not in email:
        return jsonify({"error": "A valid client email is required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Client password must be at least 8 characters."}), 400
    if get_auth_user_by_email(email):
        return jsonify({"error": "A client account with this email already exists."}), 409

    client_user_id = f"user-{uuid.uuid4().hex[:12]}"
    password_hash = generate_password_hash(password)
    try:
        create_auth_user(
            client_user_id,
            email,
            password_hash,
            display_name,
            role="user",
            managed_by_user_id=session["user_id"],
        )
    except IntegrityError:
        return jsonify({"error": "A client account with this email already exists."}), 409

    client = get_auth_user_by_email(email)
    return jsonify({"ok": True, "client": _serialize_auth_user(client)}), 201


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
        user_id = _resolve_target_user_id(session, payload.get("user_id", "anon"))
        if user_id is None:
            return jsonify({"error": "Forbidden"}), 403
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
    user_id = _resolve_target_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Forbidden"}), 403
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
    user_id = _resolve_target_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Forbidden"}), 403
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
    user_id = _resolve_target_user_id(session, requested_user_id)
    if user_id is None:
        return jsonify({"error": "Forbidden"}), 403
    data = _list_calendar(user_id)
    if data is None:
        return jsonify({"error": "calendar service unavailable"}), 502
    return jsonify(data)


@app.post("/calendar/sync")
def calendar_sync():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id = _resolve_target_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Forbidden"}), 403
    plan = body.get("plan")
    if not isinstance(plan, dict):
        plan = get_latest_plan(user_id)
    if not isinstance(plan, dict):
        return jsonify({"error": "No plan available to sync."}), 400

    plan["user_id"] = user_id
    try:
        data = _sync_calendar_for_plan(user_id, plan)
        if data is None:
            return jsonify({"error": "calendar service unavailable"}), 502
        return jsonify(data)
    except Exception as exc:
        app.logger.exception("Calendar sync failed for user %s", user_id)
        return jsonify({"error": f"Calendar sync failed: {exc}"}), 500


@app.post("/nudge/send")
def nudge_send():
    body = request.get_json(force=True)
    res = requests.post(f"{MOTIVATION_URL}/nudge/send", json=body)
    return jsonify(res.json()), res.status_code


@app.get("/user/<user_id>")
def get_user_route(user_id):
    session = _get_current_session()
    target_user_id = _resolve_target_user_id(session, user_id)
    if session and target_user_id is None:
        return jsonify({"error": "Forbidden"}), 403

    data = get_user(target_user_id or user_id)
    if not data:
        return jsonify({"exists": False})
    plan = get_latest_plan(target_user_id or user_id)
    calendar = _list_calendar(target_user_id or user_id)
    return jsonify({"exists": True, **data, "plan": plan, "calendar": calendar, "user_id": target_user_id or user_id})


@app.post("/user/<user_id>/profile")
def save_user_profile(user_id):
    session = _get_current_session()
    target_user_id = _resolve_target_user_id(session, user_id)
    if session and target_user_id is None:
        return jsonify({"error": "Forbidden"}), 403

    body = request.get_json(force=True)
    upsert_user(
        target_user_id or user_id,
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
