from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional


@dataclass
class UserProfile:
    user_id: str = "anon"
    age: Optional[int] = None
    sex: Optional[Literal["M", "F", "Other"]] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Literal[
        "sedentary", "light", "moderate", "active", "very_active"
    ] = "light"
    dietary_preferences: List[str] = field(default_factory=list)
    injuries: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    time_windows: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        return cls(**data)


@dataclass
class Goal:
    type: Literal["fat_loss", "muscle_gain", "endurance", "general_health"] = (
        "general_health"
    )
    deficit_kcal: int = 0
    target_minutes: int = 30

    @classmethod
    def from_dict(cls, data: Dict) -> "Goal":
        return cls(**data)


@dataclass
class PlanMeal:
    name: str
    calories: int
    macros: Dict[str, float]
    when: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "calories": self.calories,
            "macros": self.macros,
            "when": self.when,
        }


@dataclass
class PlanWorkout:
    name: str
    duration_min: int
    intensity: Literal["low", "medium", "high"] = "medium"
    when: Optional[str] = None
    equipment: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "duration_min": self.duration_min,
            "intensity": self.intensity,
            "when": self.when,
            "equipment": self.equipment,
        }


@dataclass
class DayPlan:
    user_id: str
    meals: List[PlanMeal] = field(default_factory=list)
    workouts: List[PlanWorkout] = field(default_factory=list)

    @property
    def total_calories(self) -> int:
        return sum(m.calories for m in self.meals)

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "meals": [m.to_dict() for m in self.meals],
            "workouts": [w.to_dict() for w in self.workouts],
            "total_calories": self.total_calories,
        }


@dataclass
class Event:
    id: str
    user_id: str
    type: Literal["meal", "workout", "nudge"]
    name: str
    scheduled_at: datetime
    duration_min: Optional[int] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "name": self.name,
            "scheduled_at": self.scheduled_at.isoformat(),
            "duration_min": self.duration_min,
            "metadata": self.metadata,
        }


@dataclass
class ScheduleRequest:
    user_id: str
    meals: List[Dict] = field(default_factory=list)
    workouts: List[Dict] = field(default_factory=list)
    windows: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "ScheduleRequest":
        windows = data.get("windows", [])
        for win in windows:
            if "-" not in win:
                raise ValueError("windows must be in HH:MM-HH:MM format")
        return cls(**data)


@dataclass
class ScheduleResponse:
    ok: bool
    events: List[Event] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {"ok": self.ok, "events": [e.to_dict() for e in self.events]}


@dataclass
class Feedback:
    event_id: str
    rating: int
    reason: Optional[str] = None
    user_id: Optional[str] = None
    bandit_arm: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "Feedback":
        rating = int(data.get("rating"))
        if rating < 1 or rating > 5:
            raise ValueError("rating must be 1-5")
        return cls(**data)


@dataclass
class NudgeRequest:
    user_id: str
    tone: Literal["coach", "friendly", "strict"] = "coach"
    goal: Literal["stay_consistent", "start", "recover"] = "stay_consistent"

    @classmethod
    def from_dict(cls, data: Dict) -> "NudgeRequest":
        return cls(**data)


@dataclass
class NudgeResponse:
    message: str
    arm_used: str

    def to_dict(self) -> Dict:
        return {"message": self.message, "arm_used": self.arm_used}
