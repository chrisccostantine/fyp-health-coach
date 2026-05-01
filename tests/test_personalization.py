from services.diet_agent.app import build_rule_based_diet
from services.exercise_agent.app import build_rule_based_exercise


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
