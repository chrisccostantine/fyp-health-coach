from __future__ import annotations

from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

from services.common.models import Event, PlanMeal, PlanWorkout, ScheduleRequest, ScheduleResponse


def _slot_to_datetime(base: datetime, slot: str) -> datetime:
    hour, minute = [int(p) for p in slot.split(":")]
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def build_schedule(request: ScheduleRequest) -> ScheduleResponse:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    events: List[Event] = []

    meals = [PlanMeal(**m) if isinstance(m, dict) else m for m in request.meals]
    workouts = [PlanWorkout(**w) if isinstance(w, dict) else w for w in request.workouts]

    windows = request.windows or ["07:00-09:00", "12:00-14:00", "18:00-20:00"]

    def pick_time(slot: str, offset_minutes: int = 0) -> datetime:
        start, _ = slot.split("-")
        return _slot_to_datetime(today, start) + timedelta(minutes=offset_minutes)

    for idx, meal in enumerate(meals):
        slot = windows[min(idx, len(windows) - 1)]
        events.append(
            Event(
                id=str(uuid4()),
                user_id=request.user_id,
                type="meal",
                name=meal.name,
                scheduled_at=pick_time(slot, offset_minutes=15 * idx),
                duration_min=15,
                metadata={"calories": meal.calories},
            )
        )

    for idx, workout in enumerate(workouts):
        slot = windows[min(len(meals) + idx, len(windows) - 1)]
        events.append(
            Event(
                id=str(uuid4()),
                user_id=request.user_id,
                type="workout",
                name=workout.name,
                scheduled_at=pick_time(slot, offset_minutes=30 * idx),
                duration_min=workout.duration_min,
                metadata={"intensity": workout.intensity},
            )
        )

    return ScheduleResponse(ok=True, events=events)
