from services.diet_agent.app import build_rule_based_diet
from services.diet_agent import app as diet_app
from services.diet_agent.kaggle_recipe_db import load_kaggle_recipe_catalog
from services.diet_agent.nutrition_db import RECIPE_CATALOG, calculate_recipe_nutrition
from services.exercise_agent.app import WORKOUT_LIBRARY, build_rule_based_exercise
from services.exercise_agent.workout_csv_db import load_workout_catalog
from services.gateway.app import _build_day_workouts, _build_month_plan


def use_local_recipe_catalog(monkeypatch):
    monkeypatch.setenv("KAGGLE_RECIPE_CSV", "__missing_test_recipe_file__.csv")
    load_kaggle_recipe_catalog.cache_clear()


def use_local_workout_catalog(monkeypatch):
    monkeypatch.setenv("WORKOUT_CSV", "__missing_test_workout_file__.csv")
    load_workout_catalog.cache_clear()


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


def test_exercise_can_use_mega_gym_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "megaGymDataset.csv"
    csv_path.write_text(
        "\n".join(
            [
                ",Title,Desc,Type,BodyPart,Equipment,Level,Rating,RatingDesc",
                "0,Banded crunch,Core exercise with a band.,Strength,Abdominals,Bands,Beginner,4.0,Good",
                "1,Dumbbell bench press,Press dumbbells from a bench.,Strength,Chest,Dumbbell,Intermediate,4.5,Great",
                "2,Treadmill run,Run at a steady pace.,Cardio,Quadriceps,Machine,Beginner,4.1,Good",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORKOUT_CSV", str(csv_path))
    load_workout_catalog.cache_clear()

    plan = build_rule_based_exercise(
        {"preferences": {"workout_location": "home", "workout_duration_pref": "20_30"}},
        {"type": "muscle_gain"},
        ["bands", "dumbbells"],
    )

    assert plan["workout_source"] == "mega_gym"
    assert plan["workouts"]
    assert all(workout["description"] for workout in plan["workouts"])
    assert all(workout["video_url"].startswith("https://www.youtube.com/results?") for workout in plan["workouts"])
    load_workout_catalog.cache_clear()


def test_recipe_nutrition_is_calculated_from_ingredient_grams():
    recipe = RECIPE_CATALOG[0]
    calculated = calculate_recipe_nutrition(recipe["ingredients_detail"])
    assert calculated == recipe["nutrition"]


def test_diet_respects_vegan_preference_and_preferred_vegetables(monkeypatch):
    use_local_recipe_catalog(monkeypatch)
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


def test_diet_filters_allergy_ingredients(monkeypatch):
    use_local_recipe_catalog(monkeypatch)
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


def test_diet_uses_realistic_daily_calories_and_protein(monkeypatch):
    use_local_recipe_catalog(monkeypatch)
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


def test_diet_can_use_kaggle_recipe_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "recipe_final.csv"
    csv_path.write_text(
        "\n".join(
            [
                "recipe_name,calories,fat,carbohydrates,protein,ingredients_list,description",
                "\"Lentil Tomato Bowl\",430,10,55,28,\"['lentils','tomato','rice']\",\"Cook lentils with tomato and serve over rice.\"",
                "\"Chickpea Cucumber Plate\",390,12,48,22,\"['chickpeas','cucumber','olive oil']\",\"Mix chickpeas with cucumber and olive oil.\"",
                "\"Tofu Spinach Rice\",410,11,50,30,\"['tofu','spinach','rice']\",\"Saute tofu with spinach and rice.\"",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KAGGLE_RECIPE_CSV", str(csv_path))
    load_kaggle_recipe_catalog.cache_clear()

    plan = build_rule_based_diet(
        {
            "age": 28,
            "sex": "F",
            "height_cm": 165,
            "weight_kg": 62,
            "activity_level": "light",
            "diet": {"preference": "vegan"},
        },
        {"type": "general_health", "deficit_kcal": 0},
    )

    assert plan["recipe_source"] == "kaggle"
    assert all(meal["name"] in {"Lentil Tomato Bowl", "Chickpea Cucumber Plate", "Tofu Spinach Rice"} for meal in plan["meals"])
    assert all(meal["calories"] > 0 for meal in plan["meals"])
    load_kaggle_recipe_catalog.cache_clear()


def test_diet_can_use_epicurious_one_hot_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "epi_r.csv"
    csv_path.write_text(
        "\n".join(
            [
                "title,rating,calories,protein,fat,sodium,healthy,vegetarian,lentil,tomato,chicken",
                "\"Lentil Tomato Soup\",4.2,360,21,8,480,1,1,1,1,0",
                "\"Vegetarian Tomato Bowl\",4.0,410,24,10,520,1,1,0,1,0",
                "\"Chicken Tomato Plate\",4.5,430,35,12,600,1,0,0,1,1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KAGGLE_RECIPE_CSV", str(csv_path))
    load_kaggle_recipe_catalog.cache_clear()

    plan = build_rule_based_diet(
        {
            "age": 30,
            "sex": "F",
            "height_cm": 165,
            "weight_kg": 62,
            "activity_level": "light",
            "diet": {"preference": "vegetarian"},
        },
        {"type": "general_health", "deficit_kcal": 0},
    )

    assert plan["recipe_source"] == "kaggle"
    assert all("Chicken" not in meal["name"] for meal in plan["meals"])
    assert all(meal["macros"]["carbs"] >= 0 for meal in plan["meals"])
    assert all(meal["ingredients"] for meal in plan["meals"])
    load_kaggle_recipe_catalog.cache_clear()


def test_missing_csv_preparation_gets_generated_fallback(monkeypatch, tmp_path):
    csv_path = tmp_path / "epi_r.csv"
    csv_path.write_text(
        "\n".join(
            [
                "title,rating,calories,protein,fat,sodium,healthy,vegetarian,lentil,tomato",
                "\"Lentil Tomato Soup\",4.2,360,21,8,480,1,1,1,1",
                "\"Tomato Lentil Bowl\",4.0,410,24,10,520,1,1,1,1",
                "\"Warm Lentil Salad\",4.3,390,20,9,500,1,1,1,1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KAGGLE_RECIPE_CSV", str(csv_path))
    monkeypatch.setattr(diet_app, "client", None)
    load_kaggle_recipe_catalog.cache_clear()
    diet_app._ai_prep_description_cached.cache_clear()

    plan = build_rule_based_diet(
        {
            "age": 30,
            "sex": "F",
            "height_cm": 165,
            "weight_kg": 62,
            "activity_level": "light",
            "diet": {"preference": "vegetarian"},
        },
        {"type": "general_health", "deficit_kcal": 0},
    )

    assert all("Prepare" in meal["description"] for meal in plan["meals"])
    assert all("nutrition values" not in meal["description"] for meal in plan["meals"])
    load_kaggle_recipe_catalog.cache_clear()
    diet_app._ai_prep_description_cached.cache_clear()


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


def test_month_plan_start_offset_changes_first_day():
    meals = [
        {"name": f"Meal {idx}", "calories": 400, "macros": {"protein": 30, "carbs": 40, "fat": 10}}
        for idx in range(28)
    ]

    base_plan = _build_month_plan("demo", meals, [], span_days=7, start_offset=0)
    regenerated_plan = _build_month_plan("demo", meals, [], span_days=7, start_offset=1)

    base_names = [meal["name"] for meal in base_plan["plan_days"][0]["meals"]]
    regenerated_names = [meal["name"] for meal in regenerated_plan["plan_days"][0]["meals"]]
    assert base_names != regenerated_names


def test_diet_regeneration_id_rotates_meal_choices(monkeypatch):
    use_local_recipe_catalog(monkeypatch)

    base_plan = build_rule_based_diet(
        {"age": 30, "sex": "F", "height_cm": 165, "weight_kg": 62, "activity_level": "moderate"},
        {"type": "general_health", "deficit_kcal": 0},
        regeneration_id=0,
    )
    regenerated_plan = build_rule_based_diet(
        {"age": 30, "sex": "F", "height_cm": 165, "weight_kg": 62, "activity_level": "moderate"},
        {"type": "general_health", "deficit_kcal": 0},
        regeneration_id=1,
    )

    assert [meal["name"] for meal in base_plan["meals"]] != [
        meal["name"] for meal in regenerated_plan["meals"]
    ]
    load_kaggle_recipe_catalog.cache_clear()


def test_day_workouts_are_two_or_three_parts_at_preferred_time():
    workouts = [
        {"name": f"Workout {idx}", "duration_min": 30, "intensity": "medium", "when": "07:00"}
        for idx in range(5)
    ]
    day_workouts = _build_day_workouts(workouts, offset=2, target_minutes=45, workout_time="18:00")
    assert len(day_workouts) == 3
    assert {workout["when"] for workout in day_workouts} == {"18:00"}
    assert sum(workout["duration_min"] for workout in day_workouts) == 45


def test_exercise_regeneration_id_rotates_workout_choices(monkeypatch):
    use_local_workout_catalog(monkeypatch)
    profile = {
        "preferences": {
            "workout_location": "home",
            "workout_duration_pref": "20_30",
            "training_freq": "1_2",
            "fitness_level": "beginner",
        }
    }

    base_plan = build_rule_based_exercise(profile, {"type": "general_health"}, [], regeneration_id=0)
    regenerated_plan = build_rule_based_exercise(profile, {"type": "general_health"}, [], regeneration_id=1)

    assert [workout["name"] for workout in base_plan["workouts"][:3]] != [
        workout["name"] for workout in regenerated_plan["workouts"][:3]
    ]


def test_exercise_respects_home_duration_and_beginner_level(monkeypatch):
    use_local_workout_catalog(monkeypatch)
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


def test_exercise_avoids_injury_contraindications(monkeypatch):
    use_local_workout_catalog(monkeypatch)
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
