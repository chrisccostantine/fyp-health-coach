from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

class UserProfile(BaseModel):
    age: Optional[int] = None
    sex: Optional[Literal["M","F","Other"]] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[Literal["sedentary","light","moderate","active","very_active"]] = "light"
    diet: Optional[Dict] = None
    injuries: Optional[List[str]] = None
    equipment: Optional[List[str]] = None
    time_windows: Optional[List[str]] = None  # e.g., ["06:00-07:00", "18:00-19:00"]

class Goal(BaseModel):
    type: Literal["fat_loss","muscle_gain","endurance","general_health"] = "general_health"
    deficit_kcal: Optional[int] = 0

class PlanMeal(BaseModel):
    name: str
    calories: int
    macros: Dict[str, float]  # grams
    when: Optional[str] = None

class PlanWorkout(BaseModel):
    name: str
    duration_min: int
    intensity: Literal["low","medium","high"] = "medium"
    when: Optional[str] = None

class DayPlan(BaseModel):
    user_id: str
    meals: List[PlanMeal] = Field(default_factory=list)
    workouts: List[PlanWorkout] = Field(default_factory=list)

class Event(BaseModel):
    user_id: str
    type: Literal["meal","workout","nudge"]
    name: str
    scheduled_at: str  # ISO datetime
    duration_min: Optional[int] = None
    metadata: Optional[Dict] = None

class Feedback(BaseModel):
    event_id: str
    rating: int = Field(ge=1, le=5)
    reason: Optional[str] = None
    user_id: Optional[str] = None
