from __future__ import annotations

from services.agents.motivation import reward_arm
from services.common.models import Feedback
from services.common.storage import record_feedback


def handle_feedback(payload: Feedback):
    record_feedback(payload.event_id, payload.user_id or "anon", payload.rating, payload.reason)
    if payload.bandit_arm:
        reward_arm(payload.bandit_arm, payload.rating)
    return {"ok": True}
