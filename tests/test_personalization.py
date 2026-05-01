from services.diet_agent.app import build_rule_based_diet
from services.diet_agent.nutrition_db import RECIPE_CATALOG, calculate_recipe_nutrition
from services.exercise_agent.app import WORKOUT_LIBRARY, build_rule_based_exercise
from services.gateway.app import _build_day_workouts, _build_month_plan


def test_local_recipe_catalog_has_at_least_100_structured_recipes():
    assert len(RECIPE_CATALOG) >= 100
    sample = RECIPE_CATALOG[0]
    assert sample["ingredients_detail"]
    assert {"calories", "protein", "carbs", "fat"}.issubset(sample["nutrition"])


def test_workout_catalog_has_at_least_200_described_workouts():
    all_workouts = [workout for workouts in WORKOUT_LIBRARY.values() for workout in workouts]
    assert len(all_workouts) >= 200
    assert all(workout.get("description") for workout in all_workouts)
    assert all(str(workout.get("video_url", "")).startswith("https://www.youtube.com/results?") for workout in all_workouts)


def test_recipe_nutrition_is_calculated_from_ingredient_grams():
    recipe = RECIPE_CATALOG[0]
    calculated = calculate_recipe_nutrition(recipe["ingredients_detail"])
    assert calculated == recipe["nutrition"]


def test_diet_respects_vegan_preference_and_preferred_vegetables():
    plan = build_rule_based_diet(
        {
            "age": 28,
            "sex": "F",
            "height_cm": 165,
            "weight_kg": 62,
            "activity_level": "moderate",
            "diet": {
                "preference": "vegan",
                "preferred_vegetables": ["Broccoli", "Tomato"],
            },
        },
        {"type": "general_health", "deficit_kcal": 0},
    )

    meal_names = [meal["name"] for meal in plan["meals"]]
    assert meal_names
    assert any("Tofu" in name or "Chickpea" in name or "Lentil" in name for name in meal_names)
    assert all("Chicken" not in name and "Tuna" not in name and "Salmon" not in name for name in meal_names)
    assert all("Yogurt" not in name and "Eggs" not in name for name in meal_names)
    assert all(meal["ingredients"] for meal in plan["meals"])
    assert all(meal["description"] for meal in plan["meals"])
    assert len(plan["meal_pool"]) >= 21


def test_diet_filters_allergy_ingredients():
    plan = build_rule_based_diet(
        {
            "age": 30,
            "sex": "M",
            "height_cm": 180,
            "weight_kg": 80,
            "activity_level": "light",
            "diet": {"allergies": ["tuna"]},
        },
        {"type": "fat_loss", "deficit_kcal": 400},
    )

    assert all("Tuna" not in meal["name"] for meal in plan["meals"])


def test_diet_uses_realistic_daily_calories_and_protein():
    plan = build_rule_based_diet(
        {
            "age": 32,
            "sex": "F",
            "height_cm": 165,
            "weight_kg": 62,
            "activity_level": "light",
        },
        {"type": "fat_loss", "deficit_kcal": 300},
    )

    meal_calories = sum(meal["calories"] for meal in plan["meals"])
    meal_protein = sum(meal["macros"]["protein"] for meal in plan["meals"])
    assert 1050 <= meal_calories <= 1850
    assert meal_protein <= 140
    assert all(meal["macros"]["protein"] <= 55 for meal in plan["meals"])


def test_month_plan_does_not_repeat_meals_within_first_week():
    meals = [
        {"name": f"Meal {idx}", "calories": 400, "macros": {"protein": 30, "carbs": 40, "fat": 10}}
        for idx in range(28)
    ]
    plan = _build_month_plan("demo", meals, [], span_days=7)
    names = [
        meal["name"]
        for day in plan["plan_days"][:7]
        for meal in day["meals"]
    ]
    assert len(names) == len(set(names))


def test_day_workouts_are_two_or_three_parts_at_preferred_time():
    workouts = [
        {"name": f"Workout {idx}", "duration_min": 30, "intensity": "medium", "when": "07:00"}
        for idx in range(5)
    ]
    day_workouts = _build_day_workouts(workouts, offset=2, target_minutes=45, workout_time="18:00")
    assert len(day_workouts) == 3
    assert {workout["when"] for workout in day_workouts} == {"18:00"}
    assert sum(workout["duration_min"] for workout in day_workouts) == 45


def test_exercise_respects_home_duration_and_beginner_level():
    plan = build_rule_based_exercise(
        {
            "preferences": {
                "workout_location": "home",
                "workout_duration_pref": "10_15",
                "training_freq": "not_at_all",
                "fitness_level": "beginner",
            }
        },
        {"type": "muscle_gain"},
        ["dumbbells", "pullup_bar"],
    )

    assert plan["workouts"]
    assert all(workout["duration_min"] <= 15 for workout in plan["workouts"])
    assert all(workout["intensity"] in {"low", "medium"} for workout in plan["workouts"])
    assert all(workout["description"] for workout in plan["workouts"])
    assert all(workout["video_url"].startswith("https://www.youtube.com/results?") for workout in plan["workouts"])


def test_exercise_avoids_injury_contraindications():
    plan = build_rule_based_exercise(
        {
            "injuries": ["shoulder"],
            "preferences": {
                "workout_location": "home",
                "workout_duration_pref": "20_30",
                "training_freq": "1_2",
                "fitness_level": "beginner",
            },
        },
        {"type": "muscle_gain"},
        ["dumbbells", "pullup_bar"],
    )

    names = [workout["name"] for workout in plan["workouts"]]
    assert all("Pull-Up" not in name and "Upper Push" not in name for name in names)
