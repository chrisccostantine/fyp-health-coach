from __future__ import annotations

import ast
import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_KAGGLE_RECIPE_CSV = DATA_DIR / "recipe_final.csv"
DEFAULT_EPI_RECIPE_CSV = DATA_DIR / "epi_r.csv"


def _first(row: dict[str, Any], names: list[str], default: Any = None):
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return default


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _parse_ingredients(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value or "").strip()
    if not raw:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
            pass
    return [part.strip() for part in raw.replace("|", ",").split(",") if part.strip()]


def _one_hot_tags(row: dict[str, Any]) -> list[str]:
    reserved = {"title", "recipe_name", "name", "rating", "calories", "protein", "fat", "sodium"}
    tags: list[str] = []
    for key, value in row.items():
        label = str(key).strip()
        if not label or label.lower() in reserved:
            continue
        try:
            enabled = float(str(value).strip() or 0) > 0
        except ValueError:
            enabled = False
        if enabled:
            tags.append(label)
    return tags


def _tags_from_recipe(name: str, ingredients: list[str]) -> set[str]:
    text = f"{name} {' '.join(ingredients)}".lower()
    animal_terms = {"chicken", "beef", "turkey", "salmon", "tuna", "fish", "egg", "eggs", "yogurt", "cheese", "milk"}
    meat_terms = {"chicken", "beef", "turkey", "salmon", "tuna", "fish"}
    tags = {"external", "kaggle"}
    if not any(term in text for term in meat_terms):
        tags.add("vegetarian")
    if not any(term in text for term in animal_terms):
        tags.add("vegan")
    if any(term in text for term in ["olive oil", "feta", "chickpea", "lentil", "tomato", "cucumber"]):
        tags.add("mediterranean")
    return tags


def _recipe_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    name = str(_first(row, ["recipe_name", "name", "title", "dish name", "final_food_name"], "")).strip()
    if not name:
        return None

    calories = _number(_first(row, ["calories", "kcal", "energy_kcal", "calories(kcal)"]))
    protein = _number(_first(row, ["protein", "protein_g", "protein(g)"]))
    carbs = _number(_first(row, ["carbohydrates", "carbs", "carbohydrate", "carbs_g", "carbohydrates(g)"], -1))
    fat = _number(_first(row, ["fat", "fat_g", "fat(g)"]))
    if carbs < 0 and calories > 0:
        carbs = max(0.0, (calories - protein * 4 - fat * 9) / 4)
    if calories <= 0 or protein < 0 or carbs < 0 or fat < 0:
        return None

    one_hot_tags = _one_hot_tags(row)
    ingredients = _parse_ingredients(
        _first(row, ["ingredients_list", "ingredients", "ingredient list", "recipe_ingredients"], "")
    )
    if not ingredients:
        food_tags = [
            tag for tag in one_hot_tags
            if tag.lower() not in {"healthy", "low cal", "low fat", "low sodium", "low sugar", "dinner", "lunch", "breakfast"}
        ]
        ingredients = food_tags[:12]
    ingredient_names = {item.lower() for item in ingredients}
    ingredient_detail = [
        {"key": f"ingredient_{idx+1}", "name": item, "grams": 0}
        for idx, item in enumerate(ingredients[:20])
    ]
    description = str(
        _first(row, ["description", "directions", "instructions", "steps", "cooking instructions"], "")
        or ""
    ).strip()

    return {
        "name": name,
        "source": "kaggle",
        "ingredients": ingredient_names,
        "ingredients_detail": ingredient_detail,
        "tags": _tags_from_recipe(name, ingredients) | {tag.lower() for tag in one_hot_tags},
        "nutrition": {
            "calories": round(calories, 1),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
            "sodium": round(_number(_first(row, ["sodium", "sodium_mg"], 0)), 1),
        },
        "macros": {
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
        },
        "description": description,
        "needs_prep_ai": not bool(description),
    }


@lru_cache(maxsize=4)
def load_kaggle_recipe_catalog(path: str | None = None) -> tuple[dict[str, Any], ...]:
    configured = path or os.environ.get("KAGGLE_RECIPE_CSV", "").strip()
    if configured:
        csv_path = Path(configured)
    elif DEFAULT_KAGGLE_RECIPE_CSV.exists():
        csv_path = DEFAULT_KAGGLE_RECIPE_CSV
    else:
        csv_path = DEFAULT_EPI_RECIPE_CSV
    if not csv_path.exists():
        return tuple()

    recipes: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            recipe = _recipe_from_row(row)
            if recipe:
                recipes.append(recipe)

    return tuple(recipes)
