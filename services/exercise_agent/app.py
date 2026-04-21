import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from openai import OpenAI

# -------------------- SETUP --------------------
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, "exercise.env"))
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(__name__)

# -------------------- STATIC WORKOUTS --------------------
WORKOUT_LIBRARY = {
    "fat_loss": [
        {
            "name": "Full-Body Circuit (No Machines)",
            "duration_min": 30,
            "intensity": "high",
            "when": "18:00",
            "equipment": [],
        },
        {
            "name": "Incline Walk + Core",
            "duration_min": 25,
            "intensity": "medium",
            "when": "07:00",
            "equipment": ["treadmill"],
        },
        {
            "name": "Dumbbell MetCon Intervals",
            "duration_min": 28,
            "intensity": "high",
            "when": "17:30",
            "equipment": ["dumbbells"],
        },
    ],
    "muscle_gain": [
        {
            "name": "Upper Push (DB/Bench)",
            "duration_min": 45,
            "intensity": "medium",
            "when": "18:00",
            "equipment": ["dumbbells", "bench"],
        },
        {
            "name": "Lower Body Strength",
            "duration_min": 40,
            "intensity": "medium",
            "when": "08:00",
            "equipment": ["dumbbells"],
        },
        {
            "name": "Pull-Up Progression",
            "duration_min": 25,
            "intensity": "medium",
            "when": "19:00",
            "equipment": ["pullup_bar"],
        },
    ],
    "endurance": [
        {
            "name": "Tempo Run",
            "duration_min": 35,
            "intensity": "medium",
            "when": "18:30",
            "equipment": [],
        },
        {
            "name": "Zone 2 Ride",
            "duration_min": 50,
            "intensity": "low",
            "when": "07:30",
            "equipment": ["bike"],
        },
        {
            "name": "Rowing Intervals",
            "duration_min": 30,
            "intensity": "high",
            "when": "17:00",
            "equipment": ["rower"],
        },
    ],
    "general_health": [
        {
            "name": "Brisk Walk + Mobility",
            "duration_min": 30,
            "intensity": "low",
            "when": "19:00",
            "equipment": [],
        },
        {
            "name": "Bodyweight Strength Basics",
            "duration_min": 25,
            "intensity": "low",
            "when": "07:30",
            "equipment": [],
        },
    ],
}


def _goal_key(goal: Dict[str, Any]) -> str:
    return str(goal.get("type") or goal.get("goal") or "general_health")


def _normalize_equipment(equipment: Optional[List[str]]) -> set[str]:
    if not equipment:
        return set()
    return {
        str(item).strip().lower().replace(" ", "_")
        for item in equipment
        if str(item).strip()
    }


def _workout_matches_equipment(workout: Dict[str, Any], equipment: set[str]) -> bool:
    required = set(workout.get("equipment", []))
    if not required:
        return True
    if not equipment:
        return False
    return required.issubset(equipment)


def build_rule_based_exercise(
    profile: Dict[str, Any], goal: Dict[str, Any], equipment: Optional[List[str]] = None
) -> Dict[str, Any]:
    _ = profile
    goal_key = _goal_key(goal)
    preferred = WORKOUT_LIBRARY.get(goal_key, WORKOUT_LIBRARY["general_health"])

    equipment_set = _normalize_equipment(equipment)
    matched = [w for w in preferred if _workout_matches_equipment(w, equipment_set)]

    if not matched:
        # Fallback to workouts that do not require equipment.
        matched = [w for w in preferred if not w.get("equipment")]

    if not matched:
        matched = WORKOUT_LIBRARY["general_health"]

    workouts = [
        {
            "name": w["name"],
            "duration_min": int(w.get("duration_min", 30)),
            "intensity": w.get("intensity", "medium"),
            "when": w.get("when"),
        }
        for w in matched[:2]
    ]

    return {"workouts": workouts}


# -------------------- RULE-BASED API --------------------
@app.post("/generate_exercise")
def generate_exercise():
    body = request.get_json(force=True)
    profile = body.get("profile", {})
    goal = body.get("goal", {})
    equipment = body.get("equipment") or profile.get("equipment") or []

    plan = build_rule_based_exercise(profile, goal, equipment)
    return jsonify({"exercise_plan": plan})


@app.post("/exercise/suggest")
def exercise_suggest():
    body = request.get_json(force=True)
    profile = body.get("profile", {})
    goal = body.get("goal", {})
    equipment = body.get("equipment") or profile.get("equipment") or []

    plan = build_rule_based_exercise(profile, goal, equipment)
    return jsonify({"workouts": plan["workouts"]})


# -------------------- AI EXERCISE --------------------
def ai_exercise(user_data: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
You are a certified fitness coach.

Create a personalized workout plan.

User:
{user_data}

Return ONLY valid JSON in this format:

{{
  "workouts": [
    {{
      "name": string,
      "duration_min": number,
      "intensity": "low" | "medium" | "high",
      "when": "HH:MM"
    }}
  ]
}}
"""

    if client is None:
        profile = user_data.get("profile", {})
        goal = user_data.get("goal", {})
        equipment = user_data.get("equipment") or profile.get("equipment") or []
        return build_rule_based_exercise(profile, goal, equipment)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = _parse_response_json(resp)
    if not result:
        profile = user_data.get("profile", {})
        goal = user_data.get("goal", {})
        equipment = user_data.get("equipment") or profile.get("equipment") or []
        return build_rule_based_exercise(profile, goal, equipment)

    return {"workouts": _normalize_workouts(result.get("workouts", []))}


def _parse_response_json(resp: Any) -> Dict[str, Any]:
    choices = getattr(resp, "choices", None)
    if not choices:
        return {}

    message = choices[0].message if choices else None
    content = getattr(message, "content", None)
    if content is None:
        return {}

    raw = content if isinstance(content, str) else str(content)
    raw = raw.strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _normalize_workouts(workouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for i, workout in enumerate(workouts):
        intensity = str(workout.get("intensity", "medium")).lower()
        if intensity not in {"low", "medium", "high"}:
            intensity = "medium"

        normalized.append(
            {
                "name": workout.get("name") or workout.get("title") or f"Workout {i+1}",
                "duration_min": int(
                    workout.get("duration_min", workout.get("duration", 30)) or 30
                ),
                "intensity": intensity,
                "when": workout.get("when") or workout.get("time"),
            }
        )

    return normalized


def _normalize_plan_shape(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": plan.get("user_id", "anon"),
        "meals": plan.get("meals", []),
        "workouts": _normalize_workouts(plan.get("workouts", [])),
    }


def _ai_chat_update_plan(message: str, current_plan: Dict[str, Any]) -> Dict[str, Any]:
    if client is None:
        return {
            "assistant_reply": "I updated nothing yet because AI is not configured. Add OPENAI_API_KEY to exercise.env.",
            "updated_plan": current_plan,
        }

    schema_hint = """
Return ONLY JSON:
{
  "assistant_reply": "string",
  "updated_plan": {
    "user_id": "string",
    "meals": [],
    "workouts": [
      {
        "name": "string",
        "duration_min": 0,
        "intensity": "low|medium|high",
        "when": "HH:MM"
      }
    ]
  }
}
"""
    payload = {"message": message, "current_plan": current_plan}
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are an exercise coach. Modify workouts based on user request. Preserve meals unchanged.",
            },
            {
                "role": "user",
                "content": f"{schema_hint}\n\nInput JSON:\n{json.dumps(payload)}",
            },
        ],
    )
    data = _parse_response_json(resp)
    if not data:
        return {
            "assistant_reply": "I could not parse the AI response, so I kept your current workout plan unchanged.",
            "updated_plan": current_plan,
        }

    updated = data.get("updated_plan", current_plan)
    data["updated_plan"] = _normalize_plan_shape(updated)
    if "assistant_reply" not in data:
        data["assistant_reply"] = "Updated your workout plan."
    return data


# -------------------- AI API ROUTES --------------------
@app.post("/ai_exercise")
def ai_exercise_route():
    body = request.get_json(force=True)
    result = ai_exercise(body)
    return jsonify(result)


@app.post("/exercise/chat")
def exercise_chat():
    body = request.get_json(force=True)
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    current_plan = _normalize_plan_shape(body.get("current_plan", {}))
    data = _ai_chat_update_plan(message=message, current_plan=current_plan)
    return jsonify(data)


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8102, debug=True)
