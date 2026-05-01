from __future__ import annotations

from copy import deepcopy
from typing import Any


INGREDIENTS: dict[str, dict[str, Any]] = {
    "chicken_breast": {"name": "Chicken breast, cooked", "kcal": 165, "protein": 31, "carbs": 0, "fat": 3.6},
    "turkey_breast": {"name": "Turkey breast, cooked", "kcal": 135, "protein": 29, "carbs": 0, "fat": 1.6},
    "salmon": {"name": "Salmon, cooked", "kcal": 206, "protein": 22, "carbs": 0, "fat": 12},
    "tuna": {"name": "Tuna, canned in water", "kcal": 116, "protein": 26, "carbs": 0, "fat": 1},
    "lean_beef": {"name": "Lean beef, cooked", "kcal": 217, "protein": 26, "carbs": 0, "fat": 12},
    "eggs": {"name": "Whole eggs", "kcal": 143, "protein": 13, "carbs": 1.1, "fat": 9.5},
    "greek_yogurt": {"name": "Greek yogurt, plain", "kcal": 97, "protein": 10, "carbs": 3.6, "fat": 5},
    "cottage_cheese": {"name": "Cottage cheese", "kcal": 98, "protein": 11, "carbs": 3.4, "fat": 4.3},
    "tofu": {"name": "Firm tofu", "kcal": 144, "protein": 17, "carbs": 3, "fat": 8},
    "tempeh": {"name": "Tempeh", "kcal": 193, "protein": 20, "carbs": 9, "fat": 11},
    "lentils": {"name": "Lentils, cooked", "kcal": 116, "protein": 9, "carbs": 20, "fat": 0.4},
    "chickpeas": {"name": "Chickpeas, cooked", "kcal": 164, "protein": 8.9, "carbs": 27, "fat": 2.6},
    "black_beans": {"name": "Black beans, cooked", "kcal": 132, "protein": 8.9, "carbs": 24, "fat": 0.5},
    "edamame": {"name": "Edamame", "kcal": 121, "protein": 11, "carbs": 8.9, "fat": 5.2},
    "white_rice": {"name": "White rice, cooked", "kcal": 130, "protein": 2.7, "carbs": 28, "fat": 0.3},
    "brown_rice": {"name": "Brown rice, cooked", "kcal": 123, "protein": 2.7, "carbs": 26, "fat": 1},
    "quinoa": {"name": "Quinoa, cooked", "kcal": 120, "protein": 4.4, "carbs": 21, "fat": 1.9},
    "sweet_potato": {"name": "Sweet potato, baked", "kcal": 90, "protein": 2, "carbs": 21, "fat": 0.2},
    "oats": {"name": "Oats, dry", "kcal": 389, "protein": 16.9, "carbs": 66, "fat": 6.9},
    "whole_wheat_wrap": {"name": "Whole wheat wrap", "kcal": 310, "protein": 9, "carbs": 50, "fat": 8},
    "whole_wheat_pasta": {"name": "Whole wheat pasta, cooked", "kcal": 124, "protein": 5.3, "carbs": 27, "fat": 0.5},
    "broccoli": {"name": "Broccoli", "kcal": 35, "protein": 2.4, "carbs": 7.2, "fat": 0.4},
    "spinach": {"name": "Spinach", "kcal": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4},
    "tomato": {"name": "Tomato", "kcal": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
    "cucumber": {"name": "Cucumber", "kcal": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1},
    "bell_pepper": {"name": "Bell pepper", "kcal": 31, "protein": 1, "carbs": 6, "fat": 0.3},
    "asparagus": {"name": "Asparagus", "kcal": 20, "protein": 2.2, "carbs": 3.9, "fat": 0.1},
    "onion": {"name": "Onion", "kcal": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1},
    "eggplant": {"name": "Eggplant", "kcal": 25, "protein": 1, "carbs": 5.9, "fat": 0.2},
    "cauliflower": {"name": "Cauliflower", "kcal": 25, "protein": 1.9, "carbs": 5, "fat": 0.3},
    "cabbage": {"name": "Cabbage", "kcal": 25, "protein": 1.3, "carbs": 5.8, "fat": 0.1},
    "carrot": {"name": "Carrot", "kcal": 41, "protein": 0.9, "carbs": 10, "fat": 0.2},
    "berries": {"name": "Mixed berries", "kcal": 57, "protein": 0.7, "carbs": 14, "fat": 0.3},
    "banana": {"name": "Banana", "kcal": 89, "protein": 1.1, "carbs": 23, "fat": 0.3},
    "apple": {"name": "Apple", "kcal": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
    "avocado": {"name": "Avocado", "kcal": 160, "protein": 2, "carbs": 8.5, "fat": 14.7},
    "olive_oil": {"name": "Olive oil", "kcal": 884, "protein": 0, "carbs": 0, "fat": 100},
    "peanut_butter": {"name": "Peanut butter", "kcal": 588, "protein": 25, "carbs": 20, "fat": 50},
    "almonds": {"name": "Almonds", "kcal": 579, "protein": 21, "carbs": 22, "fat": 50},
    "hummus": {"name": "Hummus", "kcal": 166, "protein": 7.9, "carbs": 14, "fat": 9.6},
    "feta": {"name": "Feta cheese", "kcal": 264, "protein": 14, "carbs": 4.1, "fat": 21},
}


PROTEIN_OPTIONS = [
    ("Chicken", "chicken_breast", 150, {"high_protein", "mediterranean"}),
    ("Turkey", "turkey_breast", 155, {"high_protein"}),
    ("Salmon", "salmon", 140, {"high_protein", "mediterranean"}),
    ("Tuna", "tuna", 140, {"high_protein", "mediterranean"}),
    ("Lean Beef", "lean_beef", 135, {"high_protein"}),
    ("Egg", "eggs", 150, {"vegetarian", "keto"}),
    ("Greek Yogurt", "greek_yogurt", 240, {"vegetarian", "mediterranean"}),
    ("Tofu", "tofu", 180, {"vegetarian", "vegan"}),
    ("Tempeh", "tempeh", 160, {"vegetarian", "vegan"}),
    ("Lentil", "lentils", 210, {"vegetarian", "vegan", "mediterranean"}),
    ("Chickpea", "chickpeas", 210, {"vegetarian", "vegan", "mediterranean"}),
    ("Black Bean", "black_beans", 210, {"vegetarian", "vegan"}),
    ("Edamame", "edamame", 190, {"vegetarian", "vegan"}),
]

CARB_OPTIONS = [
    ("Rice", "white_rice", 170, set()),
    ("Brown Rice", "brown_rice", 180, set()),
    ("Quinoa", "quinoa", 185, {"mediterranean"}),
    ("Sweet Potato", "sweet_potato", 220, set()),
    ("Pasta", "whole_wheat_pasta", 190, set()),
    ("Wrap", "whole_wheat_wrap", 75, set()),
]

VEG_OPTIONS = [
    ("Broccoli", "broccoli", 90),
    ("Spinach Tomato", "spinach", 70, "tomato", 90),
    ("Cucumber Tomato", "cucumber", 90, "tomato", 90),
    ("Bell Pepper Onion", "bell_pepper", 80, "onion", 45),
    ("Asparagus", "asparagus", 90),
    ("Eggplant Tomato", "eggplant", 110, "tomato", 80),
    ("Cauliflower", "cauliflower", 110),
    ("Cabbage Carrot", "cabbage", 80, "carrot", 70),
]

KETO_VEG_OPTIONS = [
    ("Avocado Cucumber", "avocado", 80, "cucumber", 90),
    ("Spinach Feta", "spinach", 80, "feta", 30),
    ("Broccoli Olive Oil", "broccoli", 120, "olive_oil", 8),
    ("Asparagus Avocado", "asparagus", 100, "avocado", 70),
]

BREAKFAST_OPTIONS = [
    ("Greek Yogurt Berry Oats", [("greek_yogurt", 260), ("berries", 120), ("oats", 45), ("almonds", 12)], {"vegetarian", "mediterranean"}),
    ("Peanut Butter Banana Oats", [("oats", 55), ("banana", 120), ("peanut_butter", 18), ("greek_yogurt", 160)], {"vegetarian"}),
    ("Cottage Cheese Apple Bowl", [("cottage_cheese", 260), ("apple", 150), ("almonds", 14), ("oats", 30)], {"vegetarian"}),
    ("Tofu Chickpea Breakfast Bowl", [("tofu", 160), ("chickpeas", 120), ("spinach", 80), ("tomato", 80)], {"vegetarian", "vegan"}),
    ("Egg Avocado Plate", [("eggs", 150), ("avocado", 90), ("cucumber", 100), ("tomato", 80)], {"vegetarian", "keto"}),
    ("Edamame Quinoa Breakfast Bowl", [("edamame", 150), ("quinoa", 150), ("spinach", 70), ("tomato", 80)], {"vegetarian", "vegan"}),
]


def _ingredient_entry(key: str, grams: float) -> dict[str, Any]:
    return {"key": key, "name": INGREDIENTS[key]["name"], "grams": grams}


def calculate_recipe_nutrition(ingredients: list[dict[str, Any]]) -> dict[str, float]:
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for item in ingredients:
        data = INGREDIENTS[item["key"]]
        factor = float(item["grams"]) / 100
        totals["calories"] += data["kcal"] * factor
        totals["protein"] += data["protein"] * factor
        totals["carbs"] += data["carbs"] * factor
        totals["fat"] += data["fat"] * factor
    return {key: round(value, 1) for key, value in totals.items()}


def _recipe(name: str, ingredients: list[tuple[str, float]], tags: set[str]) -> dict[str, Any]:
    entries = [_ingredient_entry(key, grams) for key, grams in ingredients]
    nutrition = calculate_recipe_nutrition(entries)
    ingredient_names = {entry["name"].lower() for entry in entries}
    ingredient_keys = {entry["key"] for entry in entries}
    return {
        "name": name,
        "ingredients_detail": entries,
        "ingredients": ingredient_names | ingredient_keys,
        "tags": tags,
        "nutrition": nutrition,
        "macros": {
            "protein": nutrition["protein"],
            "carbs": nutrition["carbs"],
            "fat": nutrition["fat"],
        },
    }


def build_recipe_catalog() -> list[dict[str, Any]]:
    recipes: list[dict[str, Any]] = []

    for name, ingredients, tags in BREAKFAST_OPTIONS:
        recipes.append(_recipe(name, ingredients, tags))

    for protein_name, protein_key, protein_grams, protein_tags in PROTEIN_OPTIONS:
        for carb_name, carb_key, carb_grams, carb_tags in CARB_OPTIONS:
            for veg in VEG_OPTIONS:
                veg_name = veg[0]
                ingredients = [(protein_key, protein_grams), (carb_key, carb_grams), ("olive_oil", 8)]
                if len(veg) == 3:
                    ingredients.append((veg[1], veg[2]))
                else:
                    ingredients.extend([(veg[1], veg[2]), (veg[3], veg[4])])

                tags = set(protein_tags) | set(carb_tags) | {"balanced"}
                if protein_key in {"tofu", "tempeh", "lentils", "chickpeas", "black_beans", "edamame"}:
                    tags.update({"vegetarian", "vegan"})
                if protein_key in {"eggs", "greek_yogurt"}:
                    tags.add("vegetarian")
                if protein_key not in {"tofu", "tempeh", "lentils", "chickpeas", "black_beans", "edamame"}:
                    tags.discard("vegan")

                recipes.append(
                    _recipe(
                        f"{protein_name} {carb_name} Bowl with {veg_name}",
                        ingredients,
                        tags,
                    )
                )

    keto_proteins = [
        item for item in PROTEIN_OPTIONS if item[1] in {"chicken_breast", "turkey_breast", "salmon", "tuna", "lean_beef", "eggs", "tofu", "tempeh"}
    ]
    for protein_name, protein_key, protein_grams, protein_tags in keto_proteins:
        for veg in KETO_VEG_OPTIONS:
            ingredients = [(protein_key, protein_grams), ("olive_oil", 10)]
            if len(veg) == 3:
                ingredients.append((veg[1], veg[2]))
            else:
                ingredients.extend([(veg[1], veg[2]), (veg[3], veg[4])])
            tags = set(protein_tags) | {"keto", "low_carb"}
            if protein_key in {"tofu", "tempeh"}:
                tags.update({"vegetarian", "vegan"})
            elif protein_key == "eggs":
                tags.add("vegetarian")
            recipes.append(_recipe(f"{protein_name} Keto Plate with {veg[0]}", ingredients, tags))

    return recipes


RECIPE_CATALOG = build_recipe_catalog()


def scale_recipe_to_calories(recipe: dict[str, Any], target_calories: float) -> dict[str, Any]:
    scaled = deepcopy(recipe)
    current = float(recipe["nutrition"]["calories"] or 1)
    factor = max(0.55, min(1.75, float(target_calories) / current))
    scaled["ingredients_detail"] = [
        {**item, "grams": round(float(item["grams"]) * factor, 1)}
        for item in recipe["ingredients_detail"]
    ]
    nutrition = calculate_recipe_nutrition(scaled["ingredients_detail"])
    scaled["nutrition"] = nutrition
    scaled["macros"] = {
        "protein": nutrition["protein"],
        "carbs": nutrition["carbs"],
        "fat": nutrition["fat"],
    }
    return scaled
