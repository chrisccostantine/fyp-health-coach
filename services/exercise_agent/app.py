import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from openai import OpenAI
from services.exercise_agent.workout_csv_db import load_workout_catalog, workouts_by_goal

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
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["knee", "back"],
        },
        {
            "name": "Incline Walk + Core",
            "duration_min": 25,
            "intensity": "medium",
            "when": "07:00",
            "equipment": ["treadmill"],
            "locations": ["gym", "mixed"],
            "avoid_injuries": ["knee"],
        },
        {
            "name": "Dumbbell MetCon Intervals",
            "duration_min": 28,
            "intensity": "high",
            "when": "17:30",
            "equipment": ["dumbbells"],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["shoulder", "back"],
        },
    ],
    "muscle_gain": [
        {
            "name": "Upper Push (DB/Bench)",
            "duration_min": 45,
            "intensity": "medium",
            "when": "18:00",
            "equipment": ["dumbbells", "bench"],
            "locations": ["gym", "mixed"],
            "avoid_injuries": ["shoulder"],
        },
        {
            "name": "Lower Body Strength",
            "duration_min": 40,
            "intensity": "medium",
            "when": "08:00",
            "equipment": ["dumbbells"],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["knee", "back"],
        },
        {
            "name": "Pull-Up Progression",
            "duration_min": 25,
            "intensity": "medium",
            "when": "19:00",
            "equipment": ["pullup_bar"],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["shoulder", "elbow"],
        },
    ],
    "endurance": [
        {
            "name": "Tempo Run",
            "duration_min": 35,
            "intensity": "medium",
            "when": "18:30",
            "equipment": [],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["knee", "ankle"],
        },
        {
            "name": "Zone 2 Ride",
            "duration_min": 50,
            "intensity": "low",
            "when": "07:30",
            "equipment": ["bike"],
            "locations": ["gym", "mixed"],
            "avoid_injuries": [],
        },
        {
            "name": "Rowing Intervals",
            "duration_min": 30,
            "intensity": "high",
            "when": "17:00",
            "equipment": ["rower"],
            "locations": ["gym", "mixed"],
            "avoid_injuries": ["back", "shoulder"],
        },
    ],
    "general_health": [
        {
            "name": "Brisk Walk + Mobility",
            "duration_min": 30,
            "intensity": "low",
            "when": "19:00",
            "equipment": [],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": [],
        },
        {
            "name": "Bodyweight Strength Basics",
            "duration_min": 25,
            "intensity": "low",
            "when": "07:30",
            "equipment": [],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": ["wrist", "shoulder"],
        },
        {
            "name": "Chair Mobility + Core Stability",
            "duration_min": 18,
            "intensity": "low",
            "when": "12:30",
            "equipment": [],
            "locations": ["home", "gym", "mixed"],
            "avoid_injuries": [],
        },
    ],
}


WORKOUT_FOCUSES = {
    "fat_loss": [
        ("Low-Impact Cardio Circuit", [], ["home", "gym", "mixed"], ["knee"]),
        ("Dumbbell Conditioning", ["dumbbells"], ["home", "gym", "mixed"], ["shoulder", "back"]),
        ("Treadmill Incline Intervals", ["treadmill"], ["gym", "mixed"], ["knee"]),
        ("Core + Sweat Session", [], ["home", "gym", "mixed"], ["back"]),
        ("Bike Calorie Builder", ["bike"], ["gym", "mixed"], []),
        ("Kettlebell Metabolic Flow", ["kettlebell"], ["home", "gym", "mixed"], ["back", "shoulder"]),
    ],
    "muscle_gain": [
        ("Upper Body Strength", ["dumbbells"], ["home", "gym", "mixed"], ["shoulder"]),
        ("Lower Body Hypertrophy", ["dumbbells"], ["home", "gym", "mixed"], ["knee", "back"]),
        ("Push Pull Strength", ["dumbbells", "bench"], ["gym", "mixed"], ["shoulder", "elbow"]),
        ("Posterior Chain Builder", ["dumbbells"], ["home", "gym", "mixed"], ["back"]),
        ("Bodyweight Muscle Basics", [], ["home", "gym", "mixed"], ["wrist", "shoulder"]),
        ("Pull Strength Progression", ["pullup_bar"], ["home", "gym", "mixed"], ["shoulder", "elbow"]),
    ],
    "endurance": [
        ("Run Walk Endurance", [], ["home", "gym", "mixed"], ["knee", "ankle"]),
        ("Zone 2 Bike Builder", ["bike"], ["gym", "mixed"], []),
        ("Row Endurance Intervals", ["rower"], ["gym", "mixed"], ["back", "shoulder"]),
        ("Stair Climb Stamina", [], ["home", "gym", "mixed"], ["knee"]),
        ("Tempo Cardio Session", ["treadmill"], ["gym", "mixed"], ["knee", "ankle"]),
        ("Mobility Endurance Flow", [], ["home", "gym", "mixed"], []),
    ],
    "general_health": [
        ("Full-Body Mobility", [], ["home", "gym", "mixed"], []),
        ("Beginner Strength Circuit", [], ["home", "gym", "mixed"], ["wrist", "shoulder"]),
        ("Dumbbell Health Strength", ["dumbbells"], ["home", "gym", "mixed"], ["shoulder", "back"]),
        ("Walk + Core Stability", [], ["home", "gym", "mixed"], []),
        ("Balance and Posture", [], ["home", "gym", "mixed"], []),
        ("Joint-Friendly Conditioning", [], ["home", "gym", "mixed"], ["knee"]),
    ],
}

WORKOUT_STYLES = [
    ("Foundation", 20, "low", "2 rounds of controlled work with 60 seconds rest between rounds."),
    ("Progressive", 25, "medium", "3 rounds at a steady pace with 45 seconds rest between rounds."),
    ("Density", 30, "medium", "Complete quality reps for time, resting only as needed."),
    ("Intervals", 28, "high", "Alternate 40 seconds work with 20 seconds easy movement."),
    ("Strength", 40, "medium", "Use slow reps, full range of motion, and 60-90 seconds rest."),
    ("Endurance", 45, "low", "Keep a conversational pace and focus on smooth breathing."),
    ("Power", 32, "high", "Move explosively only if form stays clean; rest 60 seconds."),
    ("Recovery", 18, "low", "Keep intensity easy and prioritize mobility and breathing."),
    ("Tempo", 35, "medium", "Use a steady pace you can maintain without form breakdown."),
    ("Challenge", 50, "high", "Push the final round while keeping one rep in reserve."),
]


def _workout_description(name: str, style_note: str, equipment: list[str]) -> str:
    equipment_text = "bodyweight only" if not equipment else ", ".join(equipment).replace("_", " ")
    return (
        f"{name}: warm up for 5 minutes, then follow the session structure. "
        f"Equipment: {equipment_text}. {style_note} Finish with 3-5 minutes of stretching."
    )


def _workout_video_url(name: str, equipment: list[str] | None = None) -> str:
    equipment_text = " ".join(str(item).replace("_", " ") for item in (equipment or []) if item)
    query = f"{name} exercise demonstration proper form"
    if equipment_text:
        query = f"{name} {equipment_text} exercise demonstration proper form"
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _build_workout_library() -> Dict[str, List[Dict[str, Any]]]:
    library: Dict[str, List[Dict[str, Any]]] = {goal: list(items) for goal, items in WORKOUT_LIBRARY.items()}
    times = ["07:00", "08:00", "12:30", "17:30", "18:00", "19:00", "20:00"]
    for goal, focuses in WORKOUT_FOCUSES.items():
        for focus_idx, (focus, equipment, locations, avoid_injuries) in enumerate(focuses):
            for style_idx, (style, duration, intensity, style_note) in enumerate(WORKOUT_STYLES):
                name = f"{style} {focus}"
                library.setdefault(goal, []).append(
                    {
                        "name": name,
                        "duration_min": duration + ((focus_idx + style_idx) % 3) * 3,
                        "intensity": intensity,
                        "when": times[(focus_idx + style_idx) % len(times)],
                        "equipment": equipment,
                        "locations": locations,
                        "avoid_injuries": avoid_injuries,
                        "description": _workout_description(name, style_note, equipment),
                        "video_url": _workout_video_url(name, equipment),
                    }
                )
    for workouts in library.values():
        for workout in workouts:
            if not workout.get("description"):
                workout["description"] = _workout_description(
                    workout["name"],
                    "Move with control, keep breathing steady, and adjust the pace if form drops.",
                    workout.get("equipment", []),
                )
            if not workout.get("video_url"):
                workout["video_url"] = _workout_video_url(
                    workout["name"],
                    workout.get("equipment", []),
                )
    return library


WORKOUT_LIBRARY = _build_workout_library()


def _goal_key(goal: Dict[str, Any]) -> str:
    return str(goal.get("type") or goal.get("goal") or "general_health")


def _rotation_offset(value: Any, pool_size: int) -> int:
    if pool_size <= 0:
        return 0
    try:
        return int(value or 0) % pool_size
    except (TypeError, ValueError):
        return sum(ord(ch) for ch in str(value or "")) % pool_size


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


def _profile_preferences(profile: Dict[str, Any]) -> Dict[str, Any]:
    prefs = profile.get("preferences") if isinstance(profile.get("preferences"), dict) else {}
    return {
        "location": str(prefs.get("workout_location") or "mixed").strip().lower() or "mixed",
        "duration_pref": str(prefs.get("workout_duration_pref") or "auto").strip().lower(),
        "training_freq": str(prefs.get("training_freq") or "").strip().lower(),
        "fitness_level": str(prefs.get("fitness_level") or "beginner").strip().lower(),
        "injuries": [
            str(item).strip().lower()
            for item in (profile.get("injuries") or [])
            if str(item).strip()
        ],
    }


def _duration_cap(duration_pref: str) -> int | None:
    return {
        "10_15": 15,
        "20_30": 30,
        "30_40": 40,
        "40_60": 60,
    }.get(duration_pref)


def _workout_matches_preferences(workout: Dict[str, Any], prefs: Dict[str, Any]) -> bool:
    location = prefs["location"]
    locations = workout.get("locations") or ["home", "gym", "mixed"]
    if location in {"home", "gym"} and location not in locations:
        return False

    avoid = {str(item).lower() for item in workout.get("avoid_injuries", [])}
    if avoid.intersection(set(prefs["injuries"])):
        return False
    return True


def _personalize_workout(workout: Dict[str, Any], prefs: Dict[str, Any]) -> Dict[str, Any]:
    duration = int(workout.get("duration_min", 30))
    cap = _duration_cap(prefs["duration_pref"])
    if cap:
        duration = min(duration, cap)
    if prefs["training_freq"] == "not_at_all" or prefs["fitness_level"] == "beginner":
        duration = min(duration, 30)

    intensity = workout.get("intensity", "medium")
    if prefs["training_freq"] == "not_at_all" or prefs["injuries"]:
        intensity = "low" if intensity == "medium" else "medium" if intensity == "high" else intensity

    return {
        "name": workout["name"],
        "duration_min": max(10, duration),
        "intensity": intensity,
        "when": workout.get("when"),
        "description": workout.get("description") or _workout_description(
            workout["name"],
            "Move with control and stop if pain appears.",
            workout.get("equipment", []),
        ),
        "video_url": workout.get("video_url") or _workout_video_url(
            workout["name"],
            workout.get("equipment", []),
        ),
    }


def build_rule_based_exercise(
    profile: Dict[str, Any], goal: Dict[str, Any], equipment: Optional[List[str]] = None, regeneration_id: Any = None
) -> Dict[str, Any]:
    _ = profile
    goal_key = _goal_key(goal)
    external_workouts = load_workout_catalog()
    active_library = workouts_by_goal(external_workouts) if external_workouts else WORKOUT_LIBRARY
    preferred = active_library.get(goal_key, active_library["general_health"])

    equipment_set = _normalize_equipment(equipment)
    prefs = _profile_preferences(profile)
    matched = [
        w
        for w in preferred
        if _workout_matches_equipment(w, equipment_set)
        and _workout_matches_preferences(w, prefs)
    ]

    if not matched:
        # Fallback to workouts that do not require equipment.
        matched = [w for w in preferred if not w.get("equipment") and _workout_matches_preferences(w, prefs)]

    if not matched:
        matched = active_library["general_health"]

    start = _rotation_offset(regeneration_id, len(matched))
    if start:
        matched = matched[start:] + matched[:start]

    workouts = [_personalize_workout(w, prefs) for w in matched[:35]]

    return {"workouts": workouts, "workout_source": "mega_gym" if external_workouts else "local"}


# -------------------- RULE-BASED API --------------------
@app.post("/generate_exercise")
def generate_exercise():
    body = request.get_json(force=True)
    profile = body.get("profile", {})
    goal = body.get("goal", {})
    equipment = body.get("equipment") or profile.get("equipment") or []

    plan = build_rule_based_exercise(profile, goal, equipment, body.get("regeneration_id"))
    return jsonify({"exercise_plan": plan})


@app.post("/exercise/suggest")
def exercise_suggest():
    body = request.get_json(force=True)
    profile = body.get("profile", {})
    goal = body.get("goal", {})
    equipment = body.get("equipment") or profile.get("equipment") or []

    plan = build_rule_based_exercise(profile, goal, equipment, body.get("regeneration_id"))
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
      "when": "HH:MM",
      "description": string,
      "video_url": string
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
                "description": workout.get("description") or workout.get("instructions"),
                "video_url": workout.get("video_url") or _workout_video_url(
                    workout.get("name") or workout.get("title") or f"Workout {i+1}",
                    workout.get("equipment", []),
                ),
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
        "when": "HH:MM",
        "description": "string",
        "video_url": "string"
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
    host = os.environ.get("EXERCISE_HOST", "127.0.0.1")
    port = int(os.environ.get("EXERCISE_PORT", "8102"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
