import hashlib
import os
from datetime import date

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Health Coach").strip()
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

MESSAGES = {
    "coach": {
        "stay_consistent": [
            "You do not need a perfect day. You need one solid choice, then another. Stay in the game today.",
            "Consistency is what changes a body, not random motivation. Hit today's plan and let the results catch up.",
            "Show yourself that you can keep promises to your future self. One meal, one workout, one strong day.",
        ],
        "build_strength": [
            "Strength is built by repeating the basics on ordinary days. Today's session still counts.",
            "Muscle comes from patient work stacked over time. Eat well, train well, and let the process do its job.",
            "Your body adapts to what you repeat. Give it another strong signal today.",
        ],
        "keep_moving": [
            "Endurance grows when you keep showing up even before you feel ready. Start and let momentum carry you.",
            "A steady pace beats waiting for the perfect mood. Move today and your energy will follow.",
            "Your stamina is built one honest session at a time. Keep your rhythm today.",
        ],
        "feel_better_daily": [
            "Healthy routines are not punishment. They are how you build a day that feels lighter and stronger.",
            "A calm, healthy day starts with a few good decisions. Keep today simple and steady.",
            "You are building a body that supports your life better every week. Today's choices matter.",
        ],
    },
    "friendly": {
        "stay_consistent": [
            "A small healthy choice today is enough to keep your streak alive. You are doing better than you think.",
            "You do not have to do everything today. Just stay close to your plan and keep moving forward.",
            "Progress loves repetition. A simple good day today will help tomorrow feel easier too.",
        ],
        "build_strength": [
            "A good meal and a focused workout can do a lot for you today. Keep building, one day at a time.",
            "Your strength grows quietly in the background every time you stay with the plan.",
            "You are not starting from zero today. You are building on every solid choice you already made.",
        ],
        "keep_moving": [
            "A little movement can change the whole mood of your day. Let today be one of those days.",
            "Keep your body in motion and your energy usually follows. Even a modest session helps.",
            "You only need to begin. Once you start moving, the rest often gets easier.",
        ],
        "feel_better_daily": [
            "Your plan is here to help your day feel better, not heavier. Keep it light, steady, and kind to yourself.",
            "Taking care of yourself today can be as simple as one good meal and a little movement.",
            "Your body notices the routines you repeat. Today is another chance to care for it well.",
        ],
    },
}

GOAL_LABELS = {
    "stay_consistent": "Stay consistent",
    "build_strength": "Build strength",
    "keep_moving": "Keep moving",
    "feel_better_daily": "Feel better daily",
}


def _brevo_enabled() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


def _pick_message(*, tone: str, goal: str, user_id: str) -> str:
    tone_messages = MESSAGES.get(tone) or MESSAGES["coach"]
    options = tone_messages.get(goal) or tone_messages.get("stay_consistent") or []
    if not options:
        return "You have another chance today to do something good for your body."

    seed = f"{user_id}:{goal}:{date.today().isoformat()}"
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(options)
    return options[index]


def _plan_snapshot(meal_count: int, workout_count: int) -> str:
    parts = []
    if meal_count > 0:
        parts.append(f"{meal_count} planned meal{'s' if meal_count != 1 else ''}")
    if workout_count > 0:
        parts.append(f"{workout_count} workout{'s' if workout_count != 1 else ''}")
    if not parts:
        return "Your plan is ready whenever you are."
    if len(parts) == 1:
        return f"Today includes {parts[0]}."
    return f"Today includes {parts[0]} and {parts[1]}."


def _send_brevo_email(*, recipient_email: str, recipient_name: str, subject: str, text_content: str):
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
    res = requests.post(
        BREVO_API_URL,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY,
        },
        json=payload,
        timeout=20,
    )
    if res.status_code not in {200, 201, 202}:
        try:
            detail = res.json()
        except ValueError:
            detail = res.text
        raise RuntimeError(f"Brevo email failed: {detail}")
    return res.json()


@app.post("/nudge/send")
def nudge():
    body = request.get_json(force=True)
    tone = str(body.get("tone", "coach")).strip().lower() or "coach"
    goal = str(body.get("goal", "stay_consistent")).strip() or "stay_consistent"
    recipient_email = str(body.get("email", "")).strip()
    recipient_name = str(body.get("name", "")).strip()
    user_id = str(body.get("user_id", recipient_email or "user")).strip()
    meal_count = int(body.get("meal_count") or 0)
    workout_count = int(body.get("workout_count") or 0)

    if not recipient_email:
        return jsonify({"error": "Recipient email is required."}), 400
    if not _brevo_enabled():
        return jsonify({"error": "Brevo email is not configured."}), 503

    message = _pick_message(tone=tone, goal=goal, user_id=user_id)
    goal_label = GOAL_LABELS.get(goal, goal.replace("_", " ").title())
    subject = f"Health Coach: {goal_label} today"
    email_text = (
        f"Hi {recipient_name or 'there'},\n\n"
        f"{message}\n\n"
        f"{_plan_snapshot(meal_count, workout_count)}\n"
        "Keep showing up for yourself today.\n\n"
        "Health Coach"
    )

    try:
        email_result = _send_brevo_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            text_content=email_text,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(
        {
            "message": message,
            "goal": goal,
            "channel": "email",
            "recipient": recipient_email,
            "provider": "brevo",
            "provider_message_id": email_result.get("messageId"),
        }
    )


if __name__ == "__main__":
    host = os.environ.get("MOTIVATION_HOST", "127.0.0.1")
    port = int(os.environ.get("MOTIVATION_PORT", "8103"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
