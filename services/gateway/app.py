import json
import os
import time
import traceback
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from services.common.models import DayPlan, Goal, PlanMeal, PlanWorkout, UserProfile
from services.common.storage import (
    create_password_reset_token,
    create_private_message,
    create_auth_session,
    create_auth_user,
    create_google_oauth_state,
    delete_google_calendar_token,
    delete_auth_session,
    delete_auth_sessions_for_user,
    delete_password_reset_token,
    delete_user_account_data,
    export_user_data,
    get_google_calendar_token,
    get_auth_session,
    get_auth_user_by_email,
    get_auth_user_by_id,
    get_latest_weekly_update,
    get_nudge_settings,
    get_password_reset_token,
    is_managed_by,
    get_latest_plan,
    item_adherence_summary,
    list_item_adherence,
    list_progress_checkins,
    list_private_messages,
    list_managed_auth_users,
    list_all_nudge_settings,
    mark_nudge_sent,
    remove_managed_auth_user,
    get_user,
    init_db,
    record_audit_log,
    record_item_adherence,
    record_progress_checkin,
    save_plan,
    save_weekly_update,
    update_auth_user_password,
    upsert_google_calendar_token,
    upsert_nudge_settings,
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
NUDGE_CRON_SECRET = os.environ.get("NUDGE_CRON_SECRET", "").strip()
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Health Coach").strip()
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
PLAN_SPAN_DAYS = max(1, int(os.environ.get("PLAN_SPAN_DAYS", "30") or 30))
SESSION_TTL_HOURS = max(1, int(os.environ.get("SESSION_TTL_HOURS", "168") or 168))
AUTH_RATE_LIMITS: dict[str, list[datetime]] = {}
HEALTH_SAFETY_DISCLAIMER = (
    "Health Coach provides general wellness guidance, not medical advice. "
    "Consult a qualified clinician before changing diet or exercise if you have "
    "a medical condition, injury, pregnancy, disordered eating history, or concerning symptoms."
)
MEAL_VARIANT_LABELS = [
    "Mediterranean Style",
    "Fresh Bowl",
    "High-Protein Plate",
    "Balanced Fuel",
    "Recovery Combo",
    "Light Energy Mix",
]
SNACK_POOL = [
    {"name": "Protein Shake + Banana", "calories": 260, "macros": {"protein": 24, "carbs": 28, "fat": 5}, "when": "11:00", "description": "Blend protein powder with water or milk, then eat the banana on the side."},
    {"name": "Cottage Cheese + Apple + Cinnamon", "calories": 240, "macros": {"protein": 20, "carbs": 24, "fat": 6}, "when": "16:00", "description": "Spoon cottage cheese into a bowl, slice the apple, and top with cinnamon."},
    {"name": "Hummus + Veggie Sticks + Crackers", "calories": 250, "macros": {"protein": 10, "carbs": 28, "fat": 10}, "when": "16:30", "description": "Portion hummus with sliced vegetables and crackers for a quick savory snack."},
    {"name": "Peanut Butter Toast + Milk", "calories": 300, "macros": {"protein": 16, "carbs": 30, "fat": 12}, "when": "10:30", "description": "Toast whole-grain bread, spread peanut butter evenly, and drink milk alongside."},
    {"name": "Greek Yogurt + Honey + Granola", "calories": 280, "macros": {"protein": 18, "carbs": 32, "fat": 8}, "when": "15:30", "description": "Layer Greek yogurt with a measured serving of granola and a small drizzle of honey."},
    {"name": "Turkey Roll-Ups + Cucumber", "calories": 220, "macros": {"protein": 24, "carbs": 8, "fat": 8}, "when": "11:30", "description": "Roll turkey slices with cucumber sticks and add mustard or lemon if desired."},
    {"name": "Boiled Eggs + Tomato", "calories": 230, "macros": {"protein": 18, "carbs": 8, "fat": 14}, "when": "16:15", "description": "Boil eggs ahead of time and pair them with sliced tomato and light seasoning."},
    {"name": "Tuna Rice Cakes", "calories": 260, "macros": {"protein": 24, "carbs": 28, "fat": 5}, "when": "10:45", "description": "Top rice cakes with tuna, lemon, and herbs; keep portions measured."},
    {"name": "Edamame + Fruit", "calories": 240, "macros": {"protein": 15, "carbs": 30, "fat": 6}, "when": "15:45", "description": "Steam edamame, season lightly, and pair with one piece of fruit."},
    {"name": "Almonds + Protein Yogurt", "calories": 290, "macros": {"protein": 22, "carbs": 18, "fat": 14}, "when": "12:00", "description": "Measure almonds and mix them into high-protein yogurt for a balanced snack."},
]
WORKOUT_TIME_PREFS = {
    "morning": "07:00",
    "midday": "12:30",
    "evening": "18:00",
}

app = Flask(__name__)
CORS(app)
init_db()
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) if os.environ.get("OPENAI_API_KEY") else None


def _serialize_auth_user(user: dict):
    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user.get("display_name") or "",
        "role": user.get("role") or "user",
        "managed_by_user_id": user.get("managed_by_user_id"),
        "health_data_consent": bool(user.get("health_data_consent")),
    }
    manager_user_id = user.get("managed_by_user_id")
    if manager_user_id:
        manager = get_auth_user_by_id(manager_user_id)
        if manager:
            payload["managed_by"] = {
                "user_id": manager["user_id"],
                "email": manager["email"],
                "display_name": manager.get("display_name") or "",
            }
    return payload


def _get_token_from_request():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def _get_current_session():
    token = _get_token_from_request()
    if not token:
        return None
    session = get_auth_session(token)
    if not session:
        return None
    expires_at = session.get("expires_at")
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_dt:
                delete_auth_session(token)
                return None
        except Exception:
            delete_auth_session(token)
            return None
    return session


def _session_expiry_iso():
    return (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()


def _rate_limit_key(scope: str, email: str | None = None):
    remote = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",", 1)[0].strip()
    identity = str(email or "").strip().lower()
    return f"{scope}:{remote}:{identity}"


def _check_rate_limit(scope: str, *, email: str | None = None, max_attempts: int = 8, window_seconds: int = 900):
    key = _rate_limit_key(scope, email)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    attempts = [ts for ts in AUTH_RATE_LIMITS.get(key, []) if ts > window_start]
    if len(attempts) >= max_attempts:
        AUTH_RATE_LIMITS[key] = attempts
        return jsonify({"error": "Too many attempts. Try again later."}), 429
    attempts.append(now)
    AUTH_RATE_LIMITS[key] = attempts
    return None


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


def _resolve_view_user_id(session: dict | None, requested_user_id: str | None):
    return _resolve_target_user_id(session, requested_user_id)


def _resolve_write_user_id(session: dict | None, requested_user_id: str | None):
    if not session:
        return requested_user_id or "anon"
    own_user_id = session["user_id"]
    target_user_id = (requested_user_id or own_user_id or "").strip() or own_user_id
    if target_user_id == own_user_id:
        return target_user_id
    return None


def _resolve_plan_edit_user_id(session: dict | None, requested_user_id: str | None):
    if not session:
        return requested_user_id or "anon", "anonymous"

    own_user_id = session["user_id"]
    target_user_id = (requested_user_id or own_user_id or "").strip() or own_user_id
    if target_user_id == own_user_id:
        return target_user_id, "client"

    if (session.get("role") or "user") == "dietitian" and is_managed_by(own_user_id, target_user_id):
        return target_user_id, "dietitian"

    return None, None


def _resolve_private_chat_partner(session: dict | None, partner_user_id: str | None):
    if not session:
        return None

    own_user_id = session["user_id"]
    target_user_id = str(partner_user_id or "").strip()
    if not target_user_id or target_user_id == own_user_id:
        return None

    if (session.get("role") or "user") == "dietitian":
        if is_managed_by(own_user_id, target_user_id):
            return get_auth_user_by_id(target_user_id)
        return None

    manager_user_id = session.get("managed_by_user_id")
    if manager_user_id and manager_user_id == target_user_id:
        return get_auth_user_by_id(target_user_id)
    return None


def _serialize_private_message(message: dict):
    created_at = message.get("created_at")
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_at = created_at.isoformat()
    elif created_at is not None:
        created_at = str(created_at)

    return {
        "id": message.get("id"),
        "sender_user_id": message.get("sender_user_id"),
        "recipient_user_id": message.get("recipient_user_id"),
        "body": message.get("body") or "",
        "created_at": created_at,
    }


def _google_calendar_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI and FRONTEND_URL)


def _safe_zoneinfo(value: str | None):
    timezone_name = (value or APP_TIMEZONE or "UTC").strip() or "UTC"
    if timezone_name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return timezone.utc


def _today_iso_date() -> str:
    return datetime.now(_safe_zoneinfo(APP_TIMEZONE)).date().isoformat()


def _copy_plan_items(items):
    return [dict(item) for item in (items or [])]


def _duration_target_minutes(quiz_data: dict | None, goal_data: dict | None):
    quiz_data = quiz_data or {}
    goal_data = goal_data or {}
    pref = str(quiz_data.get("workoutDurationPref") or "").strip().lower()
    training_freq = str(quiz_data.get("trainingFreq") or "").strip().lower()
    goal_type = str(goal_data.get("type") or "general_health").strip().lower()

    if pref == "10_15":
        return 15
    if pref == "20_30":
        return 30
    if pref == "30_40":
        return 40
    if pref == "40_60":
        return 55

    if goal_type == "muscle_gain":
        return 50
    if goal_type == "endurance":
        return 45
    if training_freq == "more_3":
        return 45
    if training_freq == "3":
        return 35
    return 30


def _fitness_score_components(payload: dict):
    age = max(14, int(float(payload.get("age") or 24)))
    activity = str(payload.get("activity") or "light").strip().lower()
    fitness_level = str(payload.get("fitness_level") or "beginner").strip().lower()
    training_freq = str(payload.get("training_freq") or "").strip().lower()
    workout_pref = str(payload.get("workout_duration_pref") or "").strip().lower()
    water_intake = str(payload.get("water_intake") or "").strip().lower()
    body_type = str(payload.get("body_type") or "average").strip().lower()
    goal_type = str(payload.get("goal_type") or "general_health").strip().lower()
    pushups_level = str(payload.get("pushups_level") or "").strip().lower()
    pullups_level = str(payload.get("pullups_level") or "").strip().lower()
    additional_goals = [str(goal).strip().lower() for goal in (payload.get("additional_goals") or [])]

    score = 50.0
    score += {
        "sedentary": -10,
        "light": -2,
        "moderate": 6,
        "active": 10,
        "very_active": 14,
    }.get(activity, 0)
    score += {
        "beginner": -6,
        "amateur": 2,
        "advanced": 8,
    }.get(fitness_level, 0)
    score += {
        "not_at_all": -10,
        "1_2": -2,
        "3": 5,
        "more_3": 9,
    }.get(training_freq, 0)
    score += {
        "10_15": -2,
        "20_30": 1,
        "30_40": 4,
        "40_60": 7,
        "auto": 3,
    }.get(workout_pref, 0)
    score += {
        "lt2": -5,
        "2_6": 2,
        "7_10": 4,
        "gt10": 3,
        "coffee_tea": -3,
    }.get(water_intake, 0)
    score += {
        "lt10": -3,
        "10_20": 2,
        "21_30": 4,
        "gt30": 6,
    }.get(pushups_level, 0)
    score += {
        "none": -4,
        "lt5": 1,
        "5_10": 3,
        "gt10": 5,
    }.get(pullups_level, 0)

    if body_type == "heavy":
        score -= 4
    elif body_type == "slim":
        score += 1

    if goal_type == "endurance":
        score += 2
    elif goal_type == "muscle_gain":
        score += 1

    score += min(4, len(additional_goals))
    score = max(20, min(95, round(score)))

    age_offset = round((50 - score) / 3)
    fitness_age = max(14, min(80, age + age_offset))
    meter_percent = max(5, min(95, score))

    if score >= 80:
        band = "excellent"
    elif score >= 65:
        band = "strong"
    elif score >= 50:
        band = "improving"
    else:
        band = "needs_attention"

    return {
        "score": int(score),
        "fitness_age": int(fitness_age),
        "meter_percent": int(meter_percent),
        "band": band,
        "chronological_age": age,
    }


def _fallback_fitness_summary(assessment: dict):
    band = assessment["band"]
    if band == "excellent":
        return (
            "Your fitness signals are strong right now. The data suggests a solid training base, healthy activity pattern, and good recovery potential.\n\n"
            "Keep progressing gradually and stay consistent with hydration, recovery, and plan adherence to hold this advantage."
        )
    if band == "strong":
        return (
            "Your fitness baseline is in a good place, with a healthy mix of activity and training habits.\n\n"
            "A bit more consistency in training volume and recovery can move you closer to an elite routine."
        )
    if band == "improving":
        return (
            "Your current fitness score shows a decent starting point, but there is clear room to improve stamina, strength, and consistency.\n\n"
            "Following the plan regularly should lower your fitness age and raise your score over the coming weeks."
        )
    return (
        "Your current fitness score suggests your body would benefit from more regular training, better recovery habits, and steady daily movement.\n\n"
        "The good news is that this type of score usually improves quickly once you follow a structured plan consistently."
    )


def _safe_float(value, default: float | None = None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number else default


def _profile_bmi(profile: UserProfile) -> float | None:
    height_cm = _safe_float(profile.height_cm)
    weight_kg = _safe_float(profile.weight_kg)
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def _normalized_profile_flags(profile: UserProfile):
    diet_data = profile.diet if isinstance(profile.diet, dict) else {}
    raw_flags = []
    for key in ("conditions", "medical_conditions", "medications", "allergies", "contraindications"):
        value = diet_data.get(key)
        if isinstance(value, list):
            raw_flags.extend(value)
        elif value:
            raw_flags.append(value)
    raw_flags.extend(profile.injuries or [])
    return [str(flag).strip().lower() for flag in raw_flags if str(flag).strip()]


def _assess_plan_safety(profile: UserProfile, goal: Goal):
    warnings = []
    blocks = []
    bmi = _profile_bmi(profile)
    age = profile.age
    height_cm = _safe_float(profile.height_cm)
    weight_kg = _safe_float(profile.weight_kg)
    deficit = int(goal.deficit_kcal or 0)
    flags = _normalized_profile_flags(profile)

    if age is None or height_cm is None or weight_kg is None:
        blocks.append("Age, height, and weight are required before generating a health plan.")
    else:
        if age < 16:
            blocks.append("Personalized diet and exercise plans are not available for users under 16.")
        elif age < 18:
            warnings.append("Users under 18 should follow this plan only with parent/guardian and clinician guidance.")

        if height_cm < 120 or height_cm > 230 or weight_kg < 35 or weight_kg > 250:
            blocks.append("The profile numbers are outside the safe range this coach can plan for.")

    if bmi is not None:
        if bmi < 18.5 and goal.type == "fat_loss":
            blocks.append("Fat-loss plans are not appropriate for an underweight BMI.")
        elif bmi < 18.5:
            warnings.append("Your BMI is below the typical healthy range; get medical guidance before changing diet or training.")
        elif bmi >= 40:
            warnings.append("A BMI in this range can need medical supervision for diet and exercise changes.")

    if deficit > 1000:
        blocks.append("The requested calorie deficit is too aggressive for a general wellness plan.")
    elif deficit > 750:
        warnings.append("This calorie deficit is aggressive; consider a slower pace unless supervised by a clinician.")
    elif deficit < 0:
        warnings.append("A negative calorie deficit was provided, so nutrition targets may support weight gain.")

    high_risk_terms = {
        "pregnant",
        "pregnancy",
        "diabetes",
        "heart disease",
        "hypertension",
        "kidney disease",
        "eating disorder",
        "anorexia",
        "bulimia",
        "chest pain",
    }
    matched_flags = sorted({term for term in high_risk_terms for flag in flags if term in flag})
    if matched_flags:
        warnings.append(
            "Your profile mentions medical factors that require professional guidance before following a plan."
        )

    return {
        "blocked": bool(blocks),
        "blocks": blocks,
        "warnings": warnings,
        "bmi": bmi,
        "disclaimer": HEALTH_SAFETY_DISCLAIMER,
    }


def _plan_safety_payload(assessment: dict):
    return {
        "blocked": bool(assessment.get("blocked")),
        "warnings": assessment.get("warnings", []),
        "bmi": assessment.get("bmi"),
        "disclaimer": assessment.get("disclaimer", HEALTH_SAFETY_DISCLAIMER),
    }


def _managed_plan_review_payload(session: dict | None):
    if not session or (session.get("role") or "user") != "user":
        return None
    manager_user_id = session.get("managed_by_user_id")
    if not manager_user_id:
        return None
    return {
        "required": True,
        "status": "pending_review",
        "reviewed_by_user_id": None,
        "reviewed_at": None,
        "note": "",
        "history": [
            {
                "status": "pending_review",
                "by_user_id": session["user_id"],
                "at": datetime.now(timezone.utc).isoformat(),
                "note": "Plan generated by managed client and queued for dietitian review.",
            }
        ],
    }


def _append_plan_review(plan: dict, *, reviewer_user_id: str, status: str, note: str):
    review = dict(plan.get("review") or {})
    history = list(review.get("history") or [])
    event = {
        "status": status,
        "by_user_id": reviewer_user_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    history.append(event)
    review.update(
        {
            "required": True,
            "status": status,
            "reviewed_by_user_id": reviewer_user_id,
            "reviewed_at": event["at"],
            "note": note,
            "history": history,
        }
    )
    return {**plan, "review": review}


def _mark_plan_pending_review(plan: dict, *, actor_user_id: str, actor_role: str, note: str):
    review = dict(plan.get("review") or {})
    if not review.get("required"):
        return plan
    history = list(review.get("history") or [])
    event = {
        "status": "pending_review",
        "by_user_id": actor_user_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    history.append(event)
    review.update(
        {
            "required": True,
            "status": "pending_review",
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "note": note,
            "history": history,
            "last_edited_by_role": actor_role,
        }
    )
    return {**plan, "review": review}


def _client_with_plan_review(client: dict):
    payload = _serialize_auth_user(client)
    plan = get_latest_plan(client["user_id"])
    if isinstance(plan, dict):
        payload["plan_review"] = plan.get("review")
        payload["has_plan"] = True
    else:
        payload["plan_review"] = None
        payload["has_plan"] = False
    payload["adherence_summary"] = item_adherence_summary(client["user_id"])
    return payload


def _clamp_int(value, minimum: int, maximum: int, default: int | None = None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _latest_weight_delta(checkins: list[dict]):
    weights = [
        float(item["weight_kg"])
        for item in sorted(checkins, key=lambda row: str(row.get("checked_in_on") or ""))
        if item.get("weight_kg") is not None
    ]
    if len(weights) < 2:
        return None
    return round(weights[-1] - weights[0], 1)


def _average(values: list[int | float | None]):
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 1)


def _weekly_recommendation(user_id: str, checkins: list[dict], user_data: dict | None, plan: dict | None):
    user_data = user_data or {}
    goal = user_data.get("goal") or {}
    profile = user_data.get("profile") or {}
    goal_type = str(goal.get("type") or "general_health")
    deficit = int(goal.get("deficit_kcal") or 0)
    weight_delta = _latest_weight_delta(checkins)
    avg_meal = _average([row.get("meal_adherence") for row in checkins])
    avg_workout = _average([row.get("workout_adherence") for row in checkins])
    avg_energy = _average([row.get("energy_level") for row in checkins])
    calorie_adjustment = 0
    workout_adjustment = "keep_current"
    reasons = []

    if avg_energy is not None and avg_energy <= 2.5:
        calorie_adjustment += 100
        workout_adjustment = "reduce_intensity"
        reasons.append("Energy has been low, so next week should feel more recoverable.")

    if avg_meal is not None and avg_meal < 60:
        calorie_adjustment += 100
        reasons.append("Meal adherence is low; a less aggressive nutrition target may be easier to follow.")

    if avg_workout is not None and avg_workout < 60:
        workout_adjustment = "reduce_duration"
        reasons.append("Workout adherence is low; shorter sessions are more realistic for the next week.")
    elif avg_workout is not None and avg_workout >= 85 and (avg_energy is None or avg_energy >= 3.5):
        workout_adjustment = "progress_slightly"
        reasons.append("Workout adherence is strong, so a small progression is reasonable.")

    if weight_delta is not None:
        if goal_type == "fat_loss" and weight_delta >= 0.2 and avg_meal and avg_meal >= 75:
            calorie_adjustment -= 100
            reasons.append("Weight is not trending down despite solid meal adherence.")
        elif goal_type == "fat_loss" and weight_delta <= -1.2:
            calorie_adjustment += 100
            reasons.append("Weight is dropping quickly, so the plan should protect energy and recovery.")
        elif goal_type == "muscle_gain" and weight_delta <= 0 and avg_meal and avg_meal >= 75:
            calorie_adjustment += 150
            reasons.append("Weight is not moving up despite solid meal adherence.")

    if not reasons:
        reasons.append("Recent check-ins look steady; keep the plan consistent for another week.")

    next_deficit = max(0, deficit - calorie_adjustment) if goal_type == "fat_loss" else deficit
    if goal_type == "muscle_gain" and calorie_adjustment > 0:
        next_deficit = deficit - calorie_adjustment

    return {
        "user_id": user_id,
        "generated_on": _today_iso_date(),
        "goal_type": goal_type,
        "checkins_used": len(checkins),
        "weight_delta_kg": weight_delta,
        "averages": {
            "meal_adherence": avg_meal,
            "workout_adherence": avg_workout,
            "energy_level": avg_energy,
        },
        "adjustments": {
            "calorie_adjustment_kcal": calorie_adjustment,
            "suggested_deficit_kcal": next_deficit,
            "workout_adjustment": workout_adjustment,
        },
        "summary": _weekly_update_summary(goal_type, calorie_adjustment, workout_adjustment),
        "reasons": reasons,
        "current_plan_start": (plan or {}).get("plan_start_date"),
        "current_weight_kg": profile.get("weight_kg"),
    }


def _weekly_update_summary(goal_type: str, calorie_adjustment: int, workout_adjustment: str):
    nutrition = "Keep nutrition targets steady."
    if calorie_adjustment > 0:
        nutrition = "Ease nutrition targets slightly for better adherence and recovery."
    elif calorie_adjustment < 0:
        nutrition = "Tighten nutrition targets slightly because progress is slower than expected."

    workout = {
        "reduce_intensity": "Lower workout intensity next week.",
        "reduce_duration": "Use shorter workouts next week.",
        "progress_slightly": "Progress workouts slightly next week.",
        "keep_current": "Keep workouts steady next week.",
    }.get(workout_adjustment, "Keep workouts steady next week.")

    if goal_type == "general_health":
        nutrition = "Keep meals consistent and focus on repeatable habits."
    return f"{nutrition} {workout}"


def _parse_iso_date(value: str | None):
    try:
        return date.fromisoformat(str(value or "").strip())
    except Exception:
        return None


def _week_key(value: str | None):
    parsed = _parse_iso_date(value)
    if not parsed:
        return None
    iso_year, iso_week, _ = parsed.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _progress_lock_status(checkins: list[dict], today: str | None = None):
    current_date = today or _today_iso_date()
    current_week = _week_key(current_date)
    this_week_checkin = None
    for checkin in checkins:
        if _week_key(checkin.get("checked_in_on")) == current_week:
            this_week_checkin = checkin
            break
    return {
        "current_week": current_week,
        "locked": bool(this_week_checkin),
        "available_on": _next_week_start(current_date) if this_week_checkin else current_date,
        "checkin": this_week_checkin,
    }


def _next_week_start(value: str):
    parsed = _parse_iso_date(value) or datetime.now(timezone.utc).date()
    days_until_next_monday = 7 - parsed.weekday()
    return (parsed + timedelta(days=days_until_next_monday)).isoformat()


def _ai_fitness_summary(payload: dict, assessment: dict):
    if openai_client is None:
        return _fallback_fitness_summary(assessment)

    try:
        prompt = {
            "user_inputs": payload,
            "assessment": assessment,
            "task": "Explain this fitness score in two short motivating paragraphs. Be practical, realistic, and encouraging. Do not mention AI or formulas.",
        }
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": "You are a fitness coach explaining a computed fitness score to a user in clear, supportive language.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt),
                },
            ],
        )
        content = resp.choices[0].message.content if resp.choices else ""
        return str(content or "").strip() or _fallback_fitness_summary(assessment)
    except Exception:
        return _fallback_fitness_summary(assessment)


def _build_day_meals(base_meals: list[dict], offset: int):
    if not base_meals:
        snack = dict(SNACK_POOL[offset % len(SNACK_POOL)])
        return [snack]

    meals = []
    default_times = ["08:00", "13:00", "16:00", "19:00"]

    pool_size = len(base_meals)
    start = (offset * 3) % pool_size
    selected = [base_meals[(start + idx) % pool_size] for idx in range(min(3, pool_size))]

    for idx, meal in enumerate(selected):
        variant = dict(meal)
        base_name = str(variant.get("name") or variant.get("title") or f"Meal {idx + 1}").strip()
        variant["name"] = base_name
        variant["when"] = variant.get("when") or default_times[min(idx, len(default_times) - 1)]
        calories = int(variant.get("calories", 0) or 0)
        if calories > 0:
            variant["calories"] = max(180, calories + ((offset + idx) % 3 - 1) * 20)
        meals.append(variant)

    snack = dict(SNACK_POOL[offset % len(SNACK_POOL)])
    meals.insert(2 if len(meals) >= 2 else len(meals), snack)
    return meals


def _workout_time_from_quiz(quiz_data: dict):
    pref = str(
        quiz_data.get("workoutTimePref")
        or quiz_data.get("workout_time_pref")
        or ""
    ).strip().lower()
    if pref in WORKOUT_TIME_PREFS:
        return WORKOUT_TIME_PREFS[pref]
    return "18:00"


def _build_day_workouts(base_workouts: list[dict], offset: int, target_minutes: int, workout_time: str = "18:00"):
    if not base_workouts:
        return []

    rotated = base_workouts[(offset * 3) % len(base_workouts) :] + base_workouts[: (offset * 3) % len(base_workouts)]
    total_target = max(15, int(target_minutes or 30))
    part_count = 3 if total_target >= 35 and len(rotated) >= 3 else min(2, len(rotated))
    base_duration = max(8, total_target // part_count)
    remaining = total_target
    workouts = []

    for idx in range(part_count):
        template = dict(rotated[idx])
        template["name"] = str(template.get("name") or template.get("title") or f"Workout Part {idx + 1}").strip()
        template["when"] = workout_time
        if idx == part_count - 1:
            duration = max(8, remaining)
        else:
            duration = min(base_duration, max(8, remaining - 8 * (part_count - idx - 1)))
        template["duration_min"] = duration
        workouts.append(template)
        remaining -= duration

    return workouts


def _plan_days(plan: dict | None):
    plan = plan or {}
    plan_days = plan.get("plan_days")
    return plan_days if isinstance(plan_days, list) else []


def _find_plan_day(plan: dict | None, selected_date: str | None = None):
    plan_days = _plan_days(plan)
    if not plan_days:
        return None

    requested_date = (selected_date or plan.get("active_date") or _today_iso_date()).strip()
    for day in plan_days:
        if str(day.get("date", "")).strip() == requested_date:
            return day
    return plan_days[0]


def _plan_view_for_date(plan: dict, selected_date: str | None = None):
    active_day = _find_plan_day(plan, selected_date)
    if not active_day:
        return {
            **plan,
            "active_date": selected_date or plan.get("active_date") or _today_iso_date(),
            "meals": plan.get("meals", []) or [],
            "workouts": plan.get("workouts", []) or [],
        }

    return {
        **plan,
        "active_date": active_day.get("date") or selected_date or _today_iso_date(),
        "meals": _copy_plan_items(active_day.get("meals", [])),
        "workouts": _copy_plan_items(active_day.get("workouts", [])),
    }


def _regeneration_offset(value) -> int:
    try:
        return int(value or 0) % PLAN_SPAN_DAYS
    except (TypeError, ValueError):
        return sum(ord(ch) for ch in str(value or "")) % PLAN_SPAN_DAYS


def _local_diet_suggest(profile: UserProfile, goal: Goal, regeneration_id=None) -> dict:
    from services.diet_agent.app import build_rule_based_diet

    plan = build_rule_based_diet(profile.model_dump(), goal.model_dump(), regeneration_id)
    return {
        "meals": plan.get("meals", []),
        "meal_pool": plan.get("meal_pool", []),
        "daily_calories": plan.get("daily_calories"),
        "macros": plan.get("macros", {}),
        "agent_fallback": "diet",
    }


def _local_exercise_suggest(profile: UserProfile, goal: Goal, equipment: list, regeneration_id=None) -> dict:
    from services.exercise_agent.app import build_rule_based_exercise

    plan = build_rule_based_exercise(
        profile.model_dump(),
        goal.model_dump(),
        equipment,
        regeneration_id,
    )
    return {
        "workouts": plan.get("workouts", []),
        "agent_fallback": "exercise",
    }


def _build_month_plan(user_id: str, meals: list[dict], workouts: list[dict], span_days: int = PLAN_SPAN_DAYS, start_offset: int = 0):
    today = datetime.now(_safe_zoneinfo(APP_TIMEZONE)).date()
    base_meals = _copy_plan_items(meals)
    base_workouts = _copy_plan_items(workouts)
    user_data = get_user(user_id) or {}
    quiz_data = user_data.get("quiz_data") or {}
    goal_data = user_data.get("goal") or {}
    workout_target = _duration_target_minutes(quiz_data, goal_data)
    workout_time = _workout_time_from_quiz(quiz_data)
    plan_days = []

    for offset in range(max(1, span_days)):
        current_date = (today + timedelta(days=offset)).isoformat()
        variant_offset = start_offset + offset
        day_meals = _build_day_meals(base_meals, variant_offset)
        day_workouts = _build_day_workouts(base_workouts, variant_offset, workout_target, workout_time)

        plan_days.append(
            {
                "date": current_date,
                "meals": day_meals,
                "workouts": day_workouts,
            }
        )

    month_plan = {
        "user_id": user_id,
        "plan_kind": "monthly",
        "plan_span_days": len(plan_days),
        "plan_start_date": plan_days[0]["date"],
        "active_date": plan_days[0]["date"],
        "plan_days": plan_days,
    }
    return _plan_view_for_date(month_plan, plan_days[0]["date"])


def _plan_day_by_date(plan: dict | None) -> dict[str, dict]:
    return {
        str(day.get("date", "")).strip(): day
        for day in _plan_days(plan)
        if str(day.get("date", "")).strip()
    }


def _merge_regenerated_plan(existing_plan: dict | None, new_plan: dict, scope: str, selected_date: str | None = None) -> dict:
    if scope not in {"meals", "workouts", "day"}:
        return new_plan

    existing_days = _plan_day_by_date(existing_plan)
    new_days = _plan_days(new_plan)
    if not existing_days or not new_days:
        return new_plan

    target_date = str(selected_date or new_plan.get("active_date") or "").strip()
    merged_days = []
    for new_day in new_days:
        day_date = str(new_day.get("date", "")).strip()
        old_day = existing_days.get(day_date)
        if not old_day:
            merged_days.append(new_day)
            continue

        merged_day = {
            "date": day_date,
            "meals": _copy_plan_items(new_day.get("meals", [])),
            "workouts": _copy_plan_items(new_day.get("workouts", [])),
        }

        if scope == "meals":
            merged_day["workouts"] = _copy_plan_items(old_day.get("workouts", []))
        elif scope == "workouts":
            merged_day["meals"] = _copy_plan_items(old_day.get("meals", []))
        elif scope == "day" and target_date and day_date != target_date:
            merged_day["meals"] = _copy_plan_items(old_day.get("meals", []))
            merged_day["workouts"] = _copy_plan_items(old_day.get("workouts", []))

        merged_days.append(merged_day)

    merged_plan = {
        **new_plan,
        "plan_days": merged_days,
    }
    return _plan_view_for_date(merged_plan, target_date or new_plan.get("active_date"))


def _merge_updated_day_into_plan(existing_plan: dict | None, selected_date: str | None, updated_day_plan: dict, user_id: str):
    existing_plan = existing_plan or {}
    plan_days = _plan_days(existing_plan)
    target_date = (selected_date or existing_plan.get("active_date") or _today_iso_date()).strip()
    meals = _copy_plan_items(updated_day_plan.get("meals", []))
    workouts = _copy_plan_items(updated_day_plan.get("workouts", []))

    if not plan_days:
        return {
            "user_id": user_id,
            "meals": meals,
            "workouts": workouts,
            "active_date": target_date,
        }

    next_days = []
    replaced = False
    for day in plan_days:
        day_date = str(day.get("date", "")).strip()
        if day_date == target_date:
            next_days.append(
                {
                    "date": day_date or target_date,
                    "meals": meals,
                    "workouts": workouts,
                }
            )
            replaced = True
        else:
            next_days.append(
                {
                    "date": day.get("date"),
                    "meals": _copy_plan_items(day.get("meals", [])),
                    "workouts": _copy_plan_items(day.get("workouts", [])),
                }
            )

    if not replaced:
        next_days.append({"date": target_date, "meals": meals, "workouts": workouts})
        next_days.sort(key=lambda day: str(day.get("date", "")))

    merged = {
        **existing_plan,
        "user_id": user_id,
        "plan_kind": existing_plan.get("plan_kind") or "monthly",
        "plan_span_days": len(next_days),
        "plan_start_date": next_days[0]["date"] if next_days else target_date,
        "active_date": target_date,
        "plan_days": next_days,
    }
    return _plan_view_for_date(merged, target_date)


def _parse_hhmm_to_minutes(value: str | None) -> int | None:
    raw = str(value or "").strip()
    if len(raw) != 5 or raw[2] != ":":
        return None
    try:
        hours = int(raw[:2])
        minutes = int(raw[3:])
    except ValueError:
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def _send_nudge_via_motivation_service(*, user_id: str, email: str, name: str, tone: str, goal: str):
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "tone": tone,
        "goal": goal,
    }
    res = requests.post(f"{MOTIVATION_URL}/nudge/send", json=payload, timeout=20)
    return res


def _derive_nudge_context(user_id: str):
    user_data = get_user(user_id) or {}
    goal_data = user_data.get("goal") or {}
    plan = get_latest_plan(user_id) or {}

    goal_type = str(goal_data.get("type") or "general_health").strip().lower()
    workout_count = len(plan.get("workouts", []) or [])
    meal_count = len(plan.get("meals", []) or [])

    tone = "coach" if goal_type in {"fat_loss", "muscle_gain"} else "friendly"

    goal_map = {
        "fat_loss": "stay_consistent",
        "muscle_gain": "build_strength",
        "endurance": "keep_moving",
        "general_health": "feel_better_daily",
    }
    goal = goal_map.get(goal_type, "stay_consistent")

    return {
        "tone": tone,
        "goal": goal,
        "goal_type": goal_type,
        "workout_count": workout_count,
        "meal_count": meal_count,
    }


def _frontend_redirect(status: str) -> str:
    base = FRONTEND_URL.rstrip("/") if FRONTEND_URL else "/"
    return f"{base}?google_calendar={status}"


def _brevo_enabled() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


def _send_account_email(*, recipient_email: str, recipient_name: str, subject: str, text_content: str):
    if not _brevo_enabled():
        raise RuntimeError("Brevo email is not configured.")

    payload = {
        "sender": {
            "name": BREVO_SENDER_NAME,
            "email": BREVO_SENDER_EMAIL,
        },
        "to": [
            {
                "email": recipient_email,
                "name": recipient_name or recipient_email,
            }
        ],
        "subject": subject,
        "textContent": text_content,
    }
    response = requests.post(
        BREVO_API_URL,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY,
        },
        json=payload,
        timeout=20,
    )
    if response.status_code not in {200, 201, 202}:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Brevo email failed: {detail}")
    return response.json()


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
    health_data_consent = bool(data.get("health_data_consent"))

    rate_error = _check_rate_limit("signup", email=email, max_attempts=5, window_seconds=900)
    if rate_error:
        return rate_error
    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if role not in {"user", "dietitian"}:
        return jsonify({"error": "Role must be 'user' or 'dietitian'."}), 400
    if role == "user" and not health_data_consent:
        return jsonify({"error": "Health data consent is required for user accounts."}), 400
    if get_auth_user_by_email(email):
        return jsonify({"error": "An account with this email already exists."}), 409

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    password_hash = generate_password_hash(password)
    try:
        create_auth_user(
            user_id,
            email,
            password_hash,
            display_name,
            role=role,
            health_data_consent=health_data_consent or role == "dietitian",
        )
    except IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 409

    token = create_auth_session(user_id, _session_expiry_iso())
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
                "health_data_consent": health_data_consent or role == "dietitian",
            },
        }
    ), 201


@app.post("/auth/login")
def login():
    data = request.get_json(force=True)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    rate_error = _check_rate_limit("login", email=email, max_attempts=8, window_seconds=900)
    if rate_error:
        return rate_error
    user = get_auth_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    token = create_auth_session(user["user_id"], _session_expiry_iso())
    return jsonify({"ok": True, "token": token, "user": _serialize_auth_user(user)})


@app.post("/auth/change-password")
def change_password():
    session, error = _require_auth()
    if error:
        return error

    data = request.get_json(force=True)
    current_password = str(data.get("current_password", ""))
    new_password = str(data.get("new_password", ""))

    if not current_password:
        return jsonify({"error": "Current password is required."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400

    user = get_auth_user_by_id(session["user_id"])
    if not user or not check_password_hash(user["password_hash"], current_password):
        return jsonify({"error": "Current password is incorrect."}), 401

    update_auth_user_password(session["user_id"], generate_password_hash(new_password))
    delete_auth_sessions_for_user(session["user_id"])
    refreshed_user = get_auth_user_by_id(session["user_id"])
    token = create_auth_session(session["user_id"], _session_expiry_iso())
    return jsonify(
        {
            "ok": True,
            "message": "Password updated successfully.",
            "token": token,
            "user": _serialize_auth_user(refreshed_user),
        }
    )


@app.post("/auth/forgot-password")
def forgot_password():
    data = request.get_json(force=True)
    email = str(data.get("email", "")).strip().lower()
    rate_error = _check_rate_limit("forgot_password", email=email, max_attempts=3, window_seconds=3600)
    if rate_error:
        return rate_error
    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400

    user = get_auth_user_by_email(email)
    if user and (not FRONTEND_URL or not _brevo_enabled()):
        return jsonify({"error": "Password reset email is not configured."}), 503
    if user:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        token = create_password_reset_token(user["user_id"], expires_at)
        reset_link = f"{FRONTEND_URL.rstrip('/')}/?reset_token={token}"
        display_name = user.get("display_name") or user["email"]
        email_text = (
            f"Hi {display_name},\n\n"
            "We received a request to reset your Health Coach password.\n\n"
            f"Use this link within 1 hour:\n{reset_link}\n\n"
            "If you did not request this, you can ignore this message.\n\n"
            "Health Coach"
        )
        try:
            _send_account_email(
                recipient_email=user["email"],
                recipient_name=display_name,
                subject="Health Coach password reset",
                text_content=email_text,
            )
        except RuntimeError as exc:
            app.logger.exception("Failed to send password reset email to %s", user["email"])
            return jsonify({"error": str(exc)}), 502

    return jsonify(
        {
            "ok": True,
            "message": "If an account exists for that email, a password reset link has been sent.",
        }
    )


@app.post("/auth/reset-password")
def reset_password():
    data = request.get_json(force=True)
    token = str(data.get("token", "")).strip()
    new_password = str(data.get("new_password", ""))
    rate_error = _check_rate_limit("reset_password", email=token[:16], max_attempts=6, window_seconds=900)
    if rate_error:
        return rate_error

    if not token:
        return jsonify({"error": "Reset token is required."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400

    reset_record = get_password_reset_token(token)
    if not reset_record:
        return jsonify({"error": "This reset link is invalid or has already been used."}), 400

    expires_at = str(reset_record.get("expires_at") or "")
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except Exception:
        delete_password_reset_token(token)
        return jsonify({"error": "This reset link is invalid."}), 400
    if expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_dt:
        delete_password_reset_token(token)
        return jsonify({"error": "This reset link has expired."}), 400

    user_id = reset_record["user_id"]
    update_auth_user_password(user_id, generate_password_hash(new_password))
    delete_password_reset_token(token)
    delete_auth_sessions_for_user(user_id)
    user = get_auth_user_by_id(user_id)
    session_token = create_auth_session(user_id, _session_expiry_iso())
    return jsonify(
        {
            "ok": True,
            "message": "Password reset successfully.",
            "token": session_token,
            "user": _serialize_auth_user(user),
        }
    )


@app.get("/dietitian/clients")
def dietitian_clients():
    session, error = _require_auth()
    if error:
        return error
    role_error = _require_dietitian(session)
    if role_error:
        return role_error
    clients = list_managed_auth_users(session["user_id"])
    return jsonify({"ok": True, "clients": [_client_with_plan_review(client) for client in clients]})


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
            health_data_consent=True,
        )
    except IntegrityError:
        return jsonify({"error": "A client account with this email already exists."}), 409

    client = get_auth_user_by_email(email)
    record_audit_log(
        session["user_id"],
        client_user_id,
        "dietitian.client_created",
        {"client_email": email},
    )
    return jsonify({"ok": True, "client": _serialize_auth_user(client)}), 201


@app.post("/dietitian/clients/<client_user_id>/unsubscribe")
def dietitian_unsubscribe_client(client_user_id):
    session, error = _require_auth()
    if error:
        return error
    role_error = _require_dietitian(session)
    if role_error:
        return role_error

    removed = remove_managed_auth_user(session["user_id"], client_user_id)
    if not removed:
        return jsonify({"error": "Client subscription not found."}), 404
    record_audit_log(session["user_id"], client_user_id, "dietitian.client_unsubscribed", {})
    return jsonify({"ok": True, "client_user_id": client_user_id})


@app.get("/messages/<partner_user_id>")
def get_private_messages(partner_user_id):
    session, error = _require_auth()
    if error:
        return error

    partner = _resolve_private_chat_partner(session, partner_user_id)
    if not partner:
        return jsonify({"error": "Private chat is only available with your assigned dietitian or managed client."}), 403

    messages = list_private_messages(session["user_id"], partner_user_id)
    return jsonify(
        {
            "ok": True,
            "partner": _serialize_auth_user(partner),
            "messages": [_serialize_private_message(message) for message in messages],
        }
    )


@app.post("/messages/<partner_user_id>")
def send_private_message(partner_user_id):
    session, error = _require_auth()
    if error:
        return error

    partner = _resolve_private_chat_partner(session, partner_user_id)
    if not partner:
        return jsonify({"error": "Private chat is only available with your assigned dietitian or managed client."}), 403

    data = request.get_json(force=True)
    body = str(data.get("body", "")).strip()
    if not body:
        return jsonify({"error": "Message body is required."}), 400

    try:
        create_private_message(session["user_id"], partner_user_id, body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    messages = list_private_messages(session["user_id"], partner_user_id)
    return jsonify(
        {
            "ok": True,
            "partner": _serialize_auth_user(partner),
            "messages": [_serialize_private_message(message) for message in messages],
        }
    ), 201


@app.post("/fitness-score/estimate")
def estimate_fitness_score():
    payload = request.get_json(force=True) or {}
    assessment = _fitness_score_components(payload)
    assessment["summary"] = _ai_fitness_summary(payload, assessment)
    return jsonify({"ok": True, "assessment": assessment})


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
    started_at = time.perf_counter()
    payload = request.get_json(force=True)
    try:
        session = _get_current_session()
        user_id = _resolve_write_user_id(session, payload.get("user_id", "anon"))
        if user_id is None:
            return jsonify({"error": "Only the client can generate or update this plan."}), 403
        profile = UserProfile(**payload.get("profile", {}))
        goal = Goal(**payload.get("goal", {}))
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    safety = _assess_plan_safety(profile, goal)
    if safety["blocked"]:
        return jsonify(
            {
                "error": "This plan needs clinician review before Health Coach can generate it.",
                "safety": safety,
            }
        ), 422

    regeneration_id = payload.get("regeneration_id")
    regeneration_scope = str(payload.get("regeneration_scope") or "full").strip().lower()
    selected_date = str(payload.get("selected_date") or "").strip() or None
    equipment = payload.get("equipment", [])
    app.logger.info(
        "plan_today start user_id=%s scope=%s selected_date=%s",
        user_id,
        regeneration_scope,
        selected_date or "",
    )

    try:
        diet_res = requests.post(
            f"{DIET_URL}/diet/suggest",
            json={
                "user_id": user_id,
                "profile": profile.model_dump(),
                "goal": goal.model_dump(),
                "regeneration_id": regeneration_id,
            },
            timeout=60,
        )
        if diet_res.status_code != 200:
            return jsonify({"error": "diet agent failed", "detail": diet_res.text}), 502
        diet = diet_res.json()
    except requests.RequestException as e:
        diet = _local_diet_suggest(profile, goal, regeneration_id)

    try:
        work_res = requests.post(
            f"{EXERCISE_URL}/exercise/suggest",
            json={
                "user_id": user_id,
                "profile": profile.model_dump(),
                "goal": goal.model_dump(),
                "equipment": equipment,
                "regeneration_id": regeneration_id,
            },
            timeout=60,
        )
        if work_res.status_code != 200:
            return jsonify({"error": "exercise agent failed", "detail": work_res.text}), 502
        work = work_res.json()
    except requests.RequestException as e:
        work = _local_exercise_suggest(profile, goal, equipment, regeneration_id)

    daily_plan = DayPlan(
        user_id=user_id,
        meals=[PlanMeal(**m) for m in diet["meals"]],
        workouts=[PlanWorkout(**w) for w in work["workouts"]],
    )
    daily_payload = daily_plan.model_dump()
    meal_pool = diet.get("meal_pool") if isinstance(diet.get("meal_pool"), list) else None
    plan_payload = _build_month_plan(
        user_id,
        meal_pool or daily_payload.get("meals", []),
        daily_payload.get("workouts", []),
        start_offset=_regeneration_offset(regeneration_id),
    )
    generation_warnings = [
        warning
        for warning in [
            "Used local diet generator because the diet agent was unreachable." if diet.get("agent_fallback") else None,
            "Used local exercise generator because the exercise agent was unreachable." if work.get("agent_fallback") else None,
        ]
        if warning
    ]
    if generation_warnings:
        plan_payload["generation_warnings"] = generation_warnings
        app.logger.warning(
            "plan_today fallback user_id=%s warnings=%s",
            user_id,
            " | ".join(generation_warnings),
        )
    if regeneration_scope in {"meals", "workouts", "day"}:
        plan_payload = _merge_regenerated_plan(
            get_latest_plan(user_id),
            plan_payload,
            regeneration_scope,
            selected_date,
        )
        if generation_warnings:
            plan_payload["generation_warnings"] = generation_warnings
    review_payload = _managed_plan_review_payload(session)
    if review_payload:
        plan_payload["review"] = review_payload
    save_plan(user_id, plan_payload)
    calendar = _sync_calendar_for_plan(user_id, plan_payload)
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    app.logger.info(
        "plan_today complete user_id=%s scope=%s days=%s meals_today=%s workouts_today=%s elapsed_ms=%s",
        user_id,
        regeneration_scope,
        len(plan_payload.get("plan_days", []) or []),
        len(plan_payload.get("meals", []) or []),
        len(plan_payload.get("workouts", []) or []),
        elapsed_ms,
    )
    return jsonify({**plan_payload, "calendar": calendar, "safety": _plan_safety_payload(safety)})


@app.post("/diet/chat")
def diet_chat():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id, edit_actor = _resolve_plan_edit_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Only the client or assigned dietitian can update this plan."}), 403
    body["user_id"] = user_id
    selected_date = str(body.get("selected_date") or "").strip() or None
    res = requests.post(f"{DIET_URL}/diet/chat", json=body, timeout=30)
    data = res.json()
    updated_plan = data.get("updated_plan")
    if res.status_code == 200 and isinstance(updated_plan, dict):
        updated_plan["user_id"] = user_id
        existing_plan = get_latest_plan(user_id)
        next_plan = _merge_updated_day_into_plan(existing_plan, selected_date, updated_plan, user_id)
        if next_plan.get("review", {}).get("required"):
            note = (
                "Dietitian edited the plan. Review is still required before the client can view it."
                if edit_actor == "dietitian"
                else "Client requested a plan change. Dietitian approval is required before the updated plan is visible."
            )
            next_plan = _mark_plan_pending_review(
                next_plan,
                actor_user_id=session["user_id"] if session else user_id,
                actor_role=edit_actor or "client",
                note=note,
            )
        save_plan(user_id, next_plan)
        data["updated_plan"] = next_plan
        data["calendar"] = _sync_calendar_for_plan(user_id, next_plan)
    return jsonify(data), res.status_code


@app.post("/exercise/chat")
def exercise_chat():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id, edit_actor = _resolve_plan_edit_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Only the client or assigned dietitian can update this plan."}), 403
    body["user_id"] = user_id
    selected_date = str(body.get("selected_date") or "").strip() or None
    res = requests.post(f"{EXERCISE_URL}/exercise/chat", json=body, timeout=30)
    data = res.json()
    updated_plan = data.get("updated_plan")
    if res.status_code == 200 and isinstance(updated_plan, dict):
        updated_plan["user_id"] = user_id
        existing_plan = get_latest_plan(user_id)
        next_plan = _merge_updated_day_into_plan(existing_plan, selected_date, updated_plan, user_id)
        if next_plan.get("review", {}).get("required"):
            note = (
                "Dietitian edited the plan. Review is still required before the client can view it."
                if edit_actor == "dietitian"
                else "Client requested a plan change. Dietitian approval is required before the updated plan is visible."
            )
            next_plan = _mark_plan_pending_review(
                next_plan,
                actor_user_id=session["user_id"] if session else user_id,
                actor_role=edit_actor or "client",
                note=note,
            )
        save_plan(user_id, next_plan)
        data["updated_plan"] = next_plan
        data["calendar"] = _sync_calendar_for_plan(user_id, next_plan)
    return jsonify(data), res.status_code


@app.post("/plan/review")
def plan_review():
    session, error = _require_auth()
    if error:
        return error
    role_error = _require_dietitian(session)
    if role_error:
        return role_error

    body = request.get_json(force=True)
    client_user_id = str(body.get("client_user_id") or "").strip()
    status = str(body.get("status") or "").strip()
    note = str(body.get("note") or "").strip()

    if status not in {"approved", "changes_requested", "rejected"}:
        return jsonify({"error": "Status must be 'approved', 'changes_requested', or 'rejected'."}), 400
    if not client_user_id or not is_managed_by(session["user_id"], client_user_id):
        return jsonify({"error": "Client is not managed by this dietitian."}), 403

    plan = get_latest_plan(client_user_id)
    if not isinstance(plan, dict):
        return jsonify({"error": "No plan found for this client."}), 404

    next_plan = _append_plan_review(
        plan,
        reviewer_user_id=session["user_id"],
        status=status,
        note=note,
    )
    save_plan(client_user_id, next_plan)
    record_audit_log(
        session["user_id"],
        client_user_id,
        "dietitian.plan_reviewed",
        {"status": status, "note": note},
    )
    return jsonify({"ok": True, "plan": next_plan, "review": next_plan["review"]})


@app.get("/calendar")
def calendar_list():
    session = _get_current_session()
    requested_user_id = request.args.get("user_id", "anon")
    user_id = _resolve_view_user_id(session, requested_user_id)
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
    user_id = _resolve_write_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Only the client can sync or update this calendar."}), 403
    plan = body.get("plan")
    if not isinstance(plan, dict):
        plan = get_latest_plan(user_id)
    if not isinstance(plan, dict):
        return jsonify({"error": "No plan available to sync."}), 400

    plan = _plan_view_for_date({**plan, "user_id": user_id}, body.get("selected_date"))
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
    session = _get_current_session()
    nudge_payload = dict(body or {})
    if session:
        derived = _derive_nudge_context(session["user_id"])
        nudge_payload["email"] = session.get("email")
        nudge_payload["name"] = session.get("display_name") or session.get("email", "")
        nudge_payload["user_id"] = session["user_id"]
        nudge_payload["tone"] = derived["tone"]
        nudge_payload["goal"] = derived["goal"]
        nudge_payload["goal_type"] = derived["goal_type"]
        nudge_payload["workout_count"] = derived["workout_count"]
        nudge_payload["meal_count"] = derived["meal_count"]
    res = requests.post(f"{MOTIVATION_URL}/nudge/send", json=nudge_payload)
    return jsonify(res.json()), res.status_code


@app.get("/nudge/settings")
def nudge_settings_get():
    session, error = _require_auth()
    if error:
        return error
    try:
        derived = _derive_nudge_context(session["user_id"])
        settings = get_nudge_settings(session["user_id"]) or {
            "user_id": session["user_id"],
            "enabled": False,
            "tone": derived["tone"],
            "goal_text": derived["goal"],
            "send_time": "08:00",
            "timezone": APP_TIMEZONE,
            "last_sent_on": None,
        }
        settings["tone"] = derived["tone"]
        settings["goal_text"] = derived["goal"]
        return jsonify({"ok": True, "settings": settings})
    except Exception as exc:
        app.logger.exception("Failed to load nudge settings for user %s", session["user_id"])
        return jsonify({"error": f"Failed to load nudge settings: {exc}"}), 500


@app.post("/nudge/settings")
def nudge_settings_save():
    session, error = _require_auth()
    if error:
        return error
    try:
        body = request.get_json(force=True)
        enabled = bool(body.get("enabled"))
        send_time = str(body.get("send_time", "08:00")).strip() or "08:00"
        timezone_name = str(body.get("timezone", APP_TIMEZONE)).strip() or APP_TIMEZONE

        if len(send_time) != 5 or send_time[2] != ":":
            return jsonify({"error": "Send time must be in HH:MM format."}), 400
        _safe_zoneinfo(timezone_name)

        derived = _derive_nudge_context(session["user_id"])

        upsert_nudge_settings(
            session["user_id"],
            enabled=enabled,
            tone=derived["tone"],
            goal_text=derived["goal"],
            send_time=send_time,
            timezone=timezone_name,
        )
        settings = get_nudge_settings(session["user_id"])
        if settings:
            settings["tone"] = derived["tone"]
            settings["goal_text"] = derived["goal"]
        return jsonify({"ok": True, "settings": settings})
    except Exception as exc:
        app.logger.exception("Failed to save nudge settings for user %s", session["user_id"])
        return jsonify({"error": f"Failed to save nudge settings: {exc}"}), 500


@app.post("/nudge/run-scheduled")
def nudge_run_scheduled():
    auth_header = request.headers.get("Authorization", "")
    bearer = auth_header.split(" ", 1)[1].strip() if auth_header.startswith("Bearer ") else ""
    if not NUDGE_CRON_SECRET or bearer != NUDGE_CRON_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    sent = []
    skipped = []
    failures = []
    now_utc = datetime.now(timezone.utc)

    for settings in list_all_nudge_settings():
        user = get_auth_user_by_id(settings["user_id"])
        if not user or not user.get("email"):
            skipped.append({"user_id": settings["user_id"], "reason": "missing_user_or_email"})
            continue

        user_now = now_utc.astimezone(_safe_zoneinfo(settings.get("timezone")))
        current_minutes = user_now.hour * 60 + user_now.minute
        scheduled_minutes = _parse_hhmm_to_minutes(settings.get("send_time"))
        today = user_now.date().isoformat()
        if settings.get("last_sent_on") == today:
            skipped.append({"user_id": settings["user_id"], "reason": "already_sent_today"})
            continue
        if scheduled_minutes is None:
            skipped.append({"user_id": settings["user_id"], "reason": "invalid_send_time"})
            continue
        if current_minutes < scheduled_minutes:
            skipped.append({"user_id": settings["user_id"], "reason": "not_due_yet"})
            continue

        try:
            derived = _derive_nudge_context(user["user_id"])
            res = _send_nudge_via_motivation_service(
                user_id=user["user_id"],
                email=user["email"],
                name=user.get("display_name") or user["email"],
                tone=derived["tone"],
                goal=derived["goal"],
            )
            payload = res.json()
            if res.status_code >= 400:
                failures.append({"user_id": user["user_id"], "error": payload.get("error", res.text)})
                continue
            mark_nudge_sent(user["user_id"], today)
            sent.append({"user_id": user["user_id"], "recipient": user["email"]})
        except Exception as exc:
            failures.append({"user_id": user["user_id"], "error": str(exc)})

    return jsonify({"ok": True, "sent": sent, "skipped": skipped, "failures": failures})


@app.get("/user/<user_id>")
def get_user_route(user_id):
    session = _get_current_session()
    target_user_id = _resolve_view_user_id(session, user_id)
    if session and target_user_id is None:
        return jsonify({"error": "Forbidden"}), 403

    data = get_user(target_user_id or user_id)
    if not data:
        return jsonify({"exists": False})
    plan = get_latest_plan(target_user_id or user_id)
    calendar = _list_calendar(target_user_id or user_id)
    target_auth_user = get_auth_user_by_id(target_user_id or user_id)
    if session and session["user_id"] != (target_user_id or user_id):
        record_audit_log(session["user_id"], target_user_id or user_id, "dietitian.client_viewed", {})
    return jsonify(
        {
            "exists": True,
            **data,
            "plan": plan,
            "calendar": calendar,
            "user_id": target_user_id or user_id,
            "account": _serialize_auth_user(target_auth_user) if target_auth_user else None,
        }
    )


@app.post("/user/<user_id>/profile")
def save_user_profile(user_id):
    session = _get_current_session()
    target_user_id = _resolve_write_user_id(session, user_id)
    if session and target_user_id is None:
        return jsonify({"error": "Only the client can update this profile."}), 403

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


@app.get("/adherence")
def adherence_list():
    session, error = _require_auth()
    if error:
        return error
    requested_user_id = request.args.get("user_id") or session["user_id"]
    user_id = _resolve_view_user_id(session, requested_user_id)
    if not user_id:
        return jsonify({"error": "You do not have access to this adherence log."}), 403
    return jsonify(
        {
            "ok": True,
            "items": list_item_adherence(user_id),
            "summary": item_adherence_summary(user_id),
        }
    )


@app.post("/adherence/item")
def adherence_item():
    session, error = _require_auth()
    if error:
        return error
    body = request.get_json(force=True)
    user_id = _resolve_write_user_id(session, body.get("user_id"))
    if not user_id:
        return jsonify({"error": "Only the client can update this adherence log."}), 403

    item_key = str(body.get("item_key") or "").strip()
    item_type = str(body.get("item_type") or "").strip().lower()
    status = str(body.get("status") or "").strip().lower()
    title = str(body.get("title") or "").strip() or None
    plan_date = str(body.get("plan_date") or "").strip() or None
    note = str(body.get("note") or "").strip() or None

    valid_statuses = {
        "meal": {"ate", "missed"},
        "workout": {"done", "missed"},
    }
    if not item_key or item_type not in valid_statuses:
        return jsonify({"error": "A valid meal or workout item is required."}), 400
    if status not in valid_statuses[item_type]:
        return jsonify({"error": "A valid adherence status is required."}), 400

    record_item_adherence(
        user_id=user_id,
        item_key=item_key,
        item_type=item_type,
        title=title,
        status=status,
        plan_date=plan_date,
        note=note,
    )
    record_audit_log(
        user_id,
        session.get("managed_by_user_id"),
        "client.adherence_updated",
        {"item_type": item_type, "status": status, "title": title, "plan_date": plan_date},
    )
    return jsonify(
        {
            "ok": True,
            "items": list_item_adherence(user_id),
            "summary": item_adherence_summary(user_id),
        }
    )


@app.get("/privacy/export")
def privacy_export():
    session, error = _require_auth()
    if error:
        return error
    return jsonify({"ok": True, "export": export_user_data(session["user_id"])})


@app.delete("/privacy/delete-account")
def privacy_delete_account():
    session, error = _require_auth()
    if error:
        return error
    user_id = session["user_id"]
    record_audit_log(user_id, user_id, "privacy.account_deleted", {})
    delete_user_account_data(user_id)
    return jsonify({"ok": True, "deleted_user_id": user_id})


@app.get("/progress")
def progress_list():
    session = _get_current_session()
    requested_user_id = request.args.get("user_id", "anon")
    user_id = _resolve_view_user_id(session, requested_user_id)
    if user_id is None:
        return jsonify({"error": "Forbidden"}), 403

    checkins = list_progress_checkins(user_id, limit=12)
    latest_update = get_latest_weekly_update(user_id)
    return jsonify(
        {
            "ok": True,
            "user_id": user_id,
            "checkins": checkins,
            "weekly_lock": _progress_lock_status(checkins),
            "weekly_update": latest_update["recommendation"] if latest_update else None,
        }
    )


@app.post("/progress/check-in")
def progress_check_in():
    body = request.get_json(force=True)
    session = _get_current_session()
    user_id = _resolve_write_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Only the client can update this progress log."}), 403

    weight_kg = _safe_float(body.get("weight_kg"))
    meal_adherence = _clamp_int(body.get("meal_adherence"), 0, 100)
    workout_adherence = _clamp_int(body.get("workout_adherence"), 0, 100)
    energy_level = _clamp_int(body.get("energy_level"), 1, 5)
    notes = str(body.get("notes") or "").strip() or None
    checked_in_on = str(body.get("checked_in_on") or _today_iso_date()).strip() or _today_iso_date()

    if weight_kg is not None and (weight_kg < 30 or weight_kg > 300):
        return jsonify({"error": "Weight must be between 30kg and 300kg."}), 400
    if meal_adherence is None or workout_adherence is None or energy_level is None:
        return jsonify({"error": "Meal adherence, workout adherence, and energy level are required."}), 400

    existing_checkins = list_progress_checkins(user_id, limit=12)
    lock = _progress_lock_status(existing_checkins, checked_in_on)
    if lock["locked"]:
        return jsonify(
            {
                "error": f"Weekly check-in already saved for {lock['current_week']}.",
                "weekly_lock": lock,
            }
        ), 409

    record_progress_checkin(
        user_id,
        weight_kg=weight_kg,
        meal_adherence=meal_adherence,
        workout_adherence=workout_adherence,
        energy_level=energy_level,
        notes=notes,
        checked_in_on=checked_in_on,
    )
    checkins = list_progress_checkins(user_id, limit=12)
    return jsonify(
        {
            "ok": True,
            "user_id": user_id,
            "checkins": checkins,
            "weekly_lock": _progress_lock_status(checkins, checked_in_on),
        }
    ), 201


@app.post("/progress/weekly-update")
def progress_weekly_update():
    body = request.get_json(force=True) if request.data else {}
    session = _get_current_session()
    user_id = _resolve_write_user_id(session, body.get("user_id", "anon"))
    if user_id is None:
        return jsonify({"error": "Only the client can generate weekly updates."}), 403

    checkins = list_progress_checkins(user_id, limit=8)
    if len(checkins) < 1:
        return jsonify({"error": "Add at least one progress check-in first."}), 400

    user_data = get_user(user_id)
    latest_plan = get_latest_plan(user_id)
    recommendation = _weekly_recommendation(user_id, checkins, user_data, latest_plan)
    save_weekly_update(user_id, recommendation)
    return jsonify({"ok": True, "weekly_update": recommendation})


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
