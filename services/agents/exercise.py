from __future__ import annotations

from typing import List

from services.common.models import Goal, PlanWorkout, UserProfile

WORKOUT_LIBRARY = {
    "fat_loss": [
        PlanWorkout(
            name="Full-Body Circuit",
            duration_min=30,
            intensity="high",
            equipment=["bodyweight"],
        ),
        PlanWorkout(
            name="Incline Walk + Core",
            duration_min=30,
            intensity="medium",
            equipment=["treadmill", "bodyweight"],
        ),
    ],
    "muscle_gain": [
        PlanWorkout(
            name="Upper Push (DB/Bench)",
            duration_min=45,
            intensity="medium",
            equipment=["dumbbells", "bench"],
        ),
        PlanWorkout(
            name="Lower Body Strength",
            duration_min=40,
            intensity="medium",
            equipment=["dumbbells"],
        ),
    ],
    "endurance": [
        PlanWorkout(
            name="Tempo Run",
            duration_min=35,
            intensity="medium",
            equipment=["treadmill", "outdoor"],
        ),
        PlanWorkout(
            name="Zone 2 Ride",
            duration_min=50,
            intensity="low",
            equipment=["bike"],
        ),
    ],
    "general_health": [
        PlanWorkout(
            name="Brisk Walk + Mobility",
            duration_min=25,
            intensity="low",
            equipment=["outdoor", "bodyweight"],
        )
    ],
}


def _filter_by_equipment(workouts: List[PlanWorkout], available: List[str]) -> List[PlanWorkout]:
    if not available:
        return workouts
    available_lower = [e.lower() for e in available]
    filtered = []
    for w in workouts:
        if any(eq.lower() in available_lower for eq in w.equipment):
            filtered.append(w)
    return filtered or workouts


def plan_workouts(profile: UserProfile, goal: Goal) -> List[PlanWorkout]:
    goal_key = goal.type
    options = WORKOUT_LIBRARY.get(goal_key, WORKOUT_LIBRARY["general_health"])
    filtered = _filter_by_equipment(options, profile.equipment)

    max_minutes = goal.target_minutes or 30
    plan: List[PlanWorkout] = []
    for w in filtered:
        if w.duration_min <= max_minutes:
            plan.append(w)
    if not plan:
        plan.append(filtered[0])

    # annotate default times
    slots = ["07:00", "18:00"]
    for idx, w in enumerate(plan[: len(slots)]):
        w.when = slots[idx]
    return plan
