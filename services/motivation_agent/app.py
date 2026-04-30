import os
import requests

from flask import Flask, request, jsonify

app = Flask(__name__)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Health Coach").strip()
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

TONES = {
    "coach": [
        "Small wins stack up. Show up for just 10 minutes—momentum will do the rest.",
        "You don’t need perfect. You need consistent. Let’s get one rep closer.",
        "Future you is watching. Give them something to be proud of today."
    ],
    "friendly": [
        "You’ve got this! A little movement now makes the whole day better.",
        "Let’s knock out one healthy choice—right now. I’m with you.",
        "Quick reminder: you deserve to feel awesome. One step today!"
    ]
}


def _brevo_enabled() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


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
    tone = body.get("tone","coach")
    goal = str(body.get("goal", "stay_consistent")).strip() or "stay_consistent"
    recipient_email = str(body.get("email", "")).strip()
    recipient_name = str(body.get("name", "")).strip()
    msg = TONES.get(tone, TONES["coach"])[0]

    if not recipient_email:
        return jsonify({"error": "Recipient email is required."}), 400
    if not _brevo_enabled():
        return jsonify({"error": "Brevo email is not configured."}), 503

    subject = f"Your Health Coach motivation nudge: {goal.replace('_', ' ').title()}"
    email_text = (
        f"Hi {recipient_name or 'there'},\n\n"
        f"Here is your motivation nudge from Health Coach:\n\n"
        f"{msg}\n\n"
        f"Goal: {goal}\n\n"
        "Keep going,\n"
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
            "message": msg,
            "tone": tone,
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
