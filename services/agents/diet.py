from __future__ import annotations

from typing import List

from services.common.models import Goal, PlanMeal, UserProfile

DEFAULT_RECIPES = [
    {"name": "Greek Yogurt + Berries + Oats", "macros": {"protein": 32, "carbs": 48, "fat": 8}},
    {"name": "Chicken Quinoa Bowl", "macros": {"protein": 40, "carbs": 50, "fat": 12}},
    {"name": "Tuna Salad Wrap", "macros": {"protein": 28, "carbs": 35, "fat": 10}},
    {"name": "Lentil Veggie Stew", "macros": {"protein": 22, "carbs": 38, "fat": 7}},
    {"name": "Salmon + Rice + Greens", "macros": {"protein": 38, "carbs": 55, "fat": 14}},
]


def estimate_tdee(profile: UserProfile) -> int:
    weight = profile.weight_kg or 70
    height = profile.height_cm or 170
    age = profile.age or 30
    sex = profile.sex or "M"

    s = 5 if sex == "M" else -161
    bmr = 10 * weight + 6.25 * height - 5 * age + s
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    mult = activity_multipliers.get(profile.activity_level, 1.375)
    return int(bmr * mult)


def plan_meals(profile: UserProfile, goal: Goal) -> List[PlanMeal]:
    base = estimate_tdee(profile)
    target = max(base - goal.deficit_kcal, 1400)

    meal_slots = ["08:00", "13:00", "19:00"]
    per_meal = target // len(meal_slots)

    # Basic preference filtering
    preferred = []
    avoid = set([p.lower() for p in profile.dietary_preferences if p.startswith("no ")])
    for recipe in DEFAULT_RECIPES:
        name = recipe["name"].lower()
        if any(block.replace("no ", "") in name for block in avoid):
            continue
        preferred.append(recipe)

    selected = preferred[:3] if len(preferred) >= 3 else DEFAULT_RECIPES[:3]

    meals: List[PlanMeal] = []
    for idx, recipe in enumerate(selected):
        meals.append(
            PlanMeal(
                name=recipe["name"],
                calories=per_meal,
                macros=recipe["macros"],
                when=meal_slots[idx],
            )
        )
    return meals
