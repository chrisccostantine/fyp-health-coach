import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from openai import OpenAI

# -------------------- SETUP --------------------
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, "diet.env"))
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(__name__)

# -------------------- TDEE --------------------
def tdee(profile: Dict[str, Any]) -> int:
    # Mifflin-St Jeor
    w = profile.get("weight_kg", 70)
    h = profile.get("height_cm", 170)
    a = profile.get("age", 30)
    sex = profile.get("sex", "M")

    s = 5 if sex == "M" else -161
    bmr = 10 * w + 6.25 * h - 5 * a + s

    mult = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }.get(profile.get("activity_level", "light"), 1.375)

    return int(bmr * mult)

# -------------------- STATIC RECIPES --------------------
RECIPES = [
    {"name": "Greek Yogurt + Berries + Oats", "macros": {"protein": 35, "carbs": 50, "fat": 8}},
    {"name": "Chicken Quinoa Bowl", "macros": {"protein": 45, "carbs": 55, "fat": 12}},
    {"name": "Tuna Salad Wrap", "macros": {"protein": 30, "carbs": 35, "fat": 10}},
    {"name": "Lentil Veggie Stew", "macros": {"protein": 24, "carbs": 40, "fat": 7}},
    {"name": "Salmon + Rice + Greens", "macros": {"protein": 42, "carbs": 60, "fat": 14}},
]

MEAL_TIMES = ["08:00", "13:00", "19:00"]


def build_rule_based_diet(profile: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    base = tdee(profile)
    deficit = int(goal.get("deficit_kcal", 0) or 0)
    target = max(base - deficit, 1400)
    per = target // 3
    meals = []

    total_p = total_c = total_f = 0

    for idx, r in enumerate(RECIPES[:3]):
        p = float(r["macros"]["protein"])
        c = float(r["macros"]["carbs"])
        f = float(r["macros"]["fat"])

        total_p += p
        total_c += c
        total_f += f

        meals.append(
            {
                "name": r["name"],
                "calories": int(per),
                "macros": {"protein": p, "carbs": c, "fat": f},
                "when": MEAL_TIMES[idx] if idx < len(MEAL_TIMES) else None,
                "protein": p,
                "carbs": c,
                "fat": f,
            }
        )

    return {
        "daily_calories": int(target),
        "macros": {"protein": total_p, "carbs": total_c, "fat": total_f},
        "meals": meals,
    }

# -------------------- RULE-BASED DIET --------------------
@app.post("/generate_diet")
def generate_diet():
    body = request.get_json(force=True)

    profile = body.get("profile", {})
    goal = body.get("goal", {})
    plan = build_rule_based_diet(profile, goal)
    return jsonify({"diet_plan": plan})


@app.post("/diet/suggest")
def diet_suggest():
    body = request.get_json(force=True)
    profile = body.get("profile", {})
    goal = body.get("goal", {})

    plan = build_rule_based_diet(profile, goal)
    return jsonify(
        {
            "meals": [
                {
                    "name": m["name"],
                    "calories": int(m["calories"]),
                    "macros": m["macros"],
                    "when": m.get("when"),
                }
                for m in plan["meals"]
            ],
            "daily_calories": plan["daily_calories"],
            "macros": plan["macros"],
        }
    )

# -------------------- AI DIET --------------------
def ai_diet(user_data: dict):
    prompt = f"""
You are a sports nutritionist.

Create a personalized daily diet plan.

User:
{user_data}

Return ONLY valid JSON in this format:

{{
  "daily_calories": number,
  "macros": {{
    "protein": number,
    "carbs": number,
    "fat": number
  }},
  "meals": [
    {{
      "name": string,
      "calories": number,
      "protein": number,
      "carbs": number,
      "fat": number
    }}
  ]
}}
"""

    if client is None:
        profile = user_data.get("profile", {})
        goal = user_data.get("goal", {})
        return build_rule_based_diet(profile, goal)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    return json.loads(resp.choices[0].message.content)


def _normalize_plan_shape(plan: Dict[str, Any]) -> Dict[str, Any]:
    meals = []
    for i, meal in enumerate(plan.get("meals", [])):
        macros = meal.get("macros", {})
        p = meal.get("protein", macros.get("protein", 0))
        c = meal.get("carbs", macros.get("carbs", 0))
        f = meal.get("fat", macros.get("fat", 0))
        meals.append(
            {
                "name": meal.get("name") or meal.get("title") or f"Meal {i+1}",
                "calories": int(meal.get("calories", meal.get("kcal", 0)) or 0),
                "macros": {"protein": float(p), "carbs": float(c), "fat": float(f)},
                "when": meal.get("when") or meal.get("time"),
            }
        )

    return {
        "user_id": plan.get("user_id", "anon"),
        "meals": meals,
        "workouts": plan.get("workouts", []),
    }


def _ai_chat_update_plan(message: str, current_plan: Dict[str, Any]) -> Dict[str, Any]:
    if client is None:
        return {
            "assistant_reply": "I updated nothing yet because AI is not configured. Add OPENAI_API_KEY to diet.env.",
            "updated_plan": current_plan,
        }

    schema_hint = """
Return ONLY JSON:
{
  "assistant_reply": "string",
  "updated_plan": {
    "user_id": "string",
    "meals": [
      {
        "name": "string",
        "calories": 0,
        "macros": {"protein": 0, "carbs": 0, "fat": 0},
        "when": "HH:MM"
      }
    ],
    "workouts": []
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
                "content": "You are a diet coach. Modify meals based on user request. Preserve workouts unchanged.",
            },
            {
                "role": "user",
                "content": f"{schema_hint}\n\nInput JSON:\n{json.dumps(payload)}",
            },
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    updated = data.get("updated_plan", current_plan)
    data["updated_plan"] = _normalize_plan_shape(updated)
    if "assistant_reply" not in data:
        data["assistant_reply"] = "Updated your diet plan."
    return data

# -------------------- AI API ROUTE --------------------
@app.post("/ai_diet")
def ai_diet_route():
    body = request.get_json(force=True)
    result = ai_diet(body)
    return jsonify(result)


@app.post("/diet/chat")
def diet_chat():
    body = request.get_json(force=True)
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    current_plan = _normalize_plan_shape(body.get("current_plan", {}))
    data = _ai_chat_update_plan(message=message, current_plan=current_plan)
    return jsonify(data)

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8101, debug=True)
