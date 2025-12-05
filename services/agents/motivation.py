from __future__ import annotations

import random
from typing import Dict, List

from services.common.models import NudgeRequest, NudgeResponse
from services.common.storage import get_arms, upsert_arm

NUDGES: Dict[str, List[str]] = {
    "coach": [
        "Small steps add up—let's finish one task now.",
        "You're capable of more than you think. Crush this session.",
    ],
    "friendly": [
        "Hey! Want to move together for 10 minutes?",
        "Your future self will high-five you for this meal choice!",
    ],
    "strict": [
        "No excuses: you planned this, now execute.",
        "Discipline beats motivation—start now.",
    ],
}


def choose_arm(agent: str, default: str = "coach") -> str:
    arms = get_arms(agent)
    if not arms:
        return default
    # Simple UCB1 approximation
    total_pulls = sum(a["pulls"] for a in arms) or 1
    best_arm = default
    best_score = -1
    for a in arms:
        avg = a["reward_sum"] / a["pulls"] if a["pulls"] else 0
        exploration = (2 * (total_pulls ** 0.5)) / (a["pulls"] + 1)
        score = avg + exploration
        if score > best_score:
            best_arm = a["arm"]
            best_score = score
    return best_arm


def send_nudge(payload: NudgeRequest) -> NudgeResponse:
    arm = choose_arm("motivation", payload.tone)
    messages = NUDGES.get(arm, NUDGES["coach"])
    message = random.choice(messages)
    upsert_arm("motivation", arm, pulled=True)
    return NudgeResponse(message=message, arm_used=arm)


def reward_arm(arm: str, rating: int):
    reward = rating / 5
    upsert_arm("motivation", arm, reward=reward)
