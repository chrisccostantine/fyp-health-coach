import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from openai import OpenAI

from services.diet_agent.nutrition_db import RECIPE_CATALOG, scale_recipe_to_calories

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

MEAL_TIMES = ["08:00", "13:00", "19:00"]


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().lower()]
    return []


def _diet_preferences(profile: Dict[str, Any]) -> Dict[str, Any]:
    diet = profile.get("diet") if isinstance(profile.get("diet"), dict) else {}
    preference = str(diet.get("preference") or diet.get("diet_pref") or "none").strip().lower()
    if preference in {"i don't follow any diet", "none", "no", ""}:
        preference = "none"
    return {
        "preference": preference,
        "preferred_vegetables": _normalize_list(diet.get("preferred_vegetables")),
        "allergies": _normalize_list(diet.get("allergies")),
    }


def _recipe_matches(recipe: Dict[str, Any], prefs: Dict[str, Any]) -> bool:
    tags = set(recipe.get("tags", set()))
    ingredients = {str(item).lower() for item in recipe.get("ingredients", set())}
    preference = prefs["preference"]

    if preference in {"vegetarian", "vegan", "keto", "mediterranean"} and preference not in tags:
        return False
    if preference == "vegan" and ingredients.intersection({"yogurt", "eggs", "chicken", "tuna", "salmon"}):
        return False
    if ingredients.intersection(set(prefs["allergies"])):
        return False
    return True


def _rank_recipes(recipes: list[Dict[str, Any]], prefs: Dict[str, Any]) -> list[Dict[str, Any]]:
    preferred_vegetables = set(prefs["preferred_vegetables"])

    def score(recipe: Dict[str, Any]) -> int:
        ingredients = {str(item).lower() for item in recipe.get("ingredients", set())}
        return len(ingredients.intersection(preferred_vegetables))

    return sorted(recipes, key=score, reverse=True)


def build_rule_based_diet(profile: Dict[str, Any], goal: Dict[str, Any]) -> Dict[str, Any]:
    base = tdee(profile)
    deficit = int(goal.get("deficit_kcal", 0) or 0)
    target = max(base - deficit, 1400)
    per = target // 3
    meals = []
    prefs = _diet_preferences(profile)
    candidates = [recipe for recipe in RECIPE_CATALOG if _recipe_matches(recipe, prefs)]
    if len(candidates) < 3 and prefs["preference"] == "none":
        candidates = [
            recipe
            for recipe in RECIPE_CATALOG
            if not set(recipe.get("ingredients", set())).intersection(set(prefs["allergies"]))
        ]
    candidates = _rank_recipes(candidates or RECIPE_CATALOG, prefs)

    total_p = total_c = total_f = 0

    for idx, r in enumerate(candidates[:3]):
        scaled = scale_recipe_to_calories(r, per)
        p = float(scaled["macros"]["protein"])
        c = float(scaled["macros"]["carbs"])
        f = float(scaled["macros"]["fat"])
        calories = int(round(scaled["nutrition"]["calories"]))

        total_p += p
        total_c += c
        total_f += f

        meals.append(
            {
                "name": scaled["name"],
                "calories": calories,
                "macros": {"protein": p, "carbs": c, "fat": f},
                "when": MEAL_TIMES[idx] if idx < len(MEAL_TIMES) else None,
                "ingredients": scaled["ingredients_detail"],
                "protein": p,
                "carbs": c,
                "fat": f,
            }
        )

    return {
        "daily_calories": int(target),
        "macros": {"protein": round(total_p, 1), "carbs": round(total_c, 1), "fat": round(total_f, 1)},
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
                    "ingredients": m.get("ingredients", []),
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
    host = os.environ.get("DIET_HOST", "127.0.0.1")
    port = int(os.environ.get("DIET_PORT", "8101"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
