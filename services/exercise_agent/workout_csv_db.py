from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from urllib.parse import quote_plus


DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_WORKOUT_CSV = DATA_DIR / "megaGymDataset.csv"


def _first(row: dict[str, Any], names: list[str], default: Any = None):
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return default


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _equipment_token(value: Any) -> str:
    token = _normalize_token(value)
    aliases = {
        "bands": "bands",
        "band": "bands",
        "dumbbell": "dumbbells",
        "dumbbells": "dumbbells",
        "barbell": "barbell",
        "kettlebells": "kettlebell",
        "kettlebell": "kettlebell",
        "body_only": "",
        "bodyweight": "",
        "none": "",
        "machine": "machine",
        "cable": "cable",
        "medicine_ball": "medicine_ball",
        "exercise_ball": "exercise_ball",
        "e_z_curl_bar": "barbell",
    }
    return aliases.get(token, token)


def _intensity_from_level(level: str) -> str:
    level = level.strip().lower()
    if level == "beginner":
        return "low"
    if level == "expert":
        return "high"
    return "medium"


def _duration_from_type(workout_type: str, level: str) -> int:
    workout_type = workout_type.strip().lower()
    level = level.strip().lower()
    if workout_type in {"cardio", "plyometrics"}:
        base = 22
    elif workout_type in {"stretching", "mobility"}:
        base = 15
    else:
        base = 18
    if level == "expert":
        base += 7
    elif level == "intermediate":
        base += 4
    return base


def _locations_for_equipment(equipment: str) -> list[str]:
    if not equipment:
        return ["home", "gym", "mixed"]
    if equipment in {"dumbbells", "bands", "kettlebell", "medicine_ball", "exercise_ball"}:
        return ["home", "gym", "mixed"]
    return ["gym", "mixed"]


def _avoid_injuries(body_part: str) -> list[str]:
    text = body_part.lower()
    avoid: list[str] = []
    if any(term in text for term in ["shoulders", "chest", "traps"]):
        avoid.append("shoulder")
    if any(term in text for term in ["lower back", "middle back"]):
        avoid.append("back")
    if any(term in text for term in ["quadriceps", "hamstrings", "calves", "glutes"]):
        avoid.append("knee")
    if "forearms" in text or "biceps" in text or "triceps" in text:
        avoid.append("elbow")
    return avoid


def _goal_tags(workout_type: str, body_part: str) -> set[str]:
    text = f"{workout_type} {body_part}".lower()
    tags = {"general_health"}
    if any(term in text for term in ["strength", "powerlifting", "olympic weightlifting"]):
        tags.add("muscle_gain")
    if any(term in text for term in ["cardio", "plyometrics"]):
        tags.update({"fat_loss", "endurance"})
    if any(term in text for term in ["abdominals", "full body", "cardio"]):
        tags.add("fat_loss")
    return tags


def _video_url(name: str, equipment: list[str]) -> str:
    equipment_text = " ".join(item.replace("_", " ") for item in equipment)
    query = f"{name} {equipment_text} exercise demonstration proper form".strip()
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _workout_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    title = str(_first(row, ["Title", "name", "exercise"], "")).strip()
    if not title:
        return None
    desc = str(_first(row, ["Desc", "description", "instructions"], "") or "").strip()
    workout_type = str(_first(row, ["Type"], "Strength") or "Strength").strip()
    body_part = str(_first(row, ["BodyPart", "body_part"], "") or "").strip()
    equipment = _equipment_token(_first(row, ["Equipment"], ""))
    equipment_list = [equipment] if equipment else []
    level = str(_first(row, ["Level"], "Intermediate") or "Intermediate").strip()

    description = desc or f"{title}: perform with controlled form, steady breathing, and a full pain-free range of motion."
    return {
        "name": title,
        "duration_min": _duration_from_type(workout_type, level),
        "intensity": _intensity_from_level(level),
        "when": "18:00",
        "equipment": equipment_list,
        "locations": _locations_for_equipment(equipment),
        "avoid_injuries": _avoid_injuries(body_part),
        "description": description,
        "video_url": _video_url(title, equipment_list),
        "body_part": body_part,
        "workout_type": workout_type,
        "level": level,
        "goal_tags": _goal_tags(workout_type, body_part),
        "source": "mega_gym",
    }


@lru_cache(maxsize=4)
def load_workout_catalog(path: str | None = None) -> tuple[dict[str, Any], ...]:
    csv_path = Path(path or os.environ.get("WORKOUT_CSV", "").strip() or DEFAULT_WORKOUT_CSV)
    if not csv_path.exists():
        return tuple()
    workouts: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            workout = _workout_from_row(row)
            if workout:
                workouts.append(workout)
    return tuple(workouts)


def workouts_by_goal(workouts: tuple[dict[str, Any], ...]) -> dict[str, list[dict[str, Any]]]:
    grouped = {goal: [] for goal in ["fat_loss", "muscle_gain", "endurance", "general_health"]}
    for workout in workouts:
        for goal in workout.get("goal_tags", {"general_health"}):
            if goal in grouped:
                grouped[goal].append(dict(workout))
    return grouped
