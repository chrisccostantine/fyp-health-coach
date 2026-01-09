from flask import Flask, request, jsonify
from pydantic import BaseModel
from typing import Dict, Any

app = Flask(__name__)

def tdee(profile:Dict[str,Any])->int:
    # Mifflin-St Jeor (simple, not gender precise for MVP)
    w = profile.get("weight_kg", 70)
    h = profile.get("height_cm", 170)
    a = profile.get("age", 30)
    sex = profile.get("sex","M")
    s = 5 if sex=="M" else -161
    bmr = 10*w + 6.25*h - 5*a + s
    mult = {"sedentary":1.2,"light":1.375,"moderate":1.55,"active":1.725,"very_active":1.9}.get(profile.get("activity_level","light"),1.375)
    return int(bmr*mult)

RECIPES = [
    {"name":"Greek Yogurt + Berries + Oats", "macros":{"protein":35,"carbs":50,"fat":8}},
    {"name":"Chicken Quinoa Bowl", "macros":{"protein":45,"carbs":55,"fat":12}},
    {"name":"Tuna Salad Wrap", "macros":{"protein":30,"carbs":35,"fat":10}},
    {"name":"Lentil Veggie Stew", "macros":{"protein":24,"carbs":40,"fat":7}},
    {"name":"Salmon + Rice + Greens", "macros":{"protein":42,"carbs":60,"fat":14}},
]

@app.post("/diet/suggest")
def suggest():
    body = request.get_json(force=True)
    profile = body.get("profile",{})
    goal = body.get("goal",{})
    base = tdee(profile)
    deficit = int(goal.get("deficit_kcal", 0) or 0)
    target = max(base - deficit, 1400)

    meals = []
    # Split target calories into 3 meals (simple MVP)
    per = target // 3
    for i, r in enumerate(RECIPES[:3]):
        meals.append({
            "name": r["name"],
            "calories": per,
            "macros": r["macros"],
            "when": ["08:00","13:00","19:00"][i]
        })
    return jsonify({"meals": meals, "calorie_target": target})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8101, debug=True)
