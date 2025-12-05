from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

from services.agents.diet import plan_meals
from services.agents.exercise import plan_workouts
from services.agents.feedback import handle_feedback
from services.agents.motivation import send_nudge
from services.agents.scheduler import build_schedule
from services.common.models import (
    DayPlan,
    Feedback,
    Goal,
    NudgeRequest,
    ScheduleRequest,
    UserProfile,
)
from services.common.storage import init_db

init_db()


@dataclass
class Response:
    data: Dict[str, Any]
    status_code: int = 200

    def get_json(self):
        return self.data


class MiniClient:
    def __init__(self, routes: Dict[Tuple[str, str], Callable]):
        self.routes = routes

    def post(self, path: str, json: Dict | None = None) -> Response:
        handler = self.routes.get(("POST", path))
        if not handler:
            return Response({"error": "not found"}, status_code=404)
        return handler(json or {})

    def get(self, path: str) -> Response:
        handler = self.routes.get(("GET", path))
        if not handler:
            return Response({"error": "not found"}, status_code=404)
        return handler({})


class MiniApp:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Callable] = {}

    def post(self, path: str):
        def decorator(func: Callable):
            self.routes[("POST", path)] = func
            return func

        return decorator

    def get(self, path: str):
        def decorator(func: Callable):
            self.routes[("GET", path)] = func
            return func

        return decorator

    def test_client(self) -> MiniClient:
        return MiniClient(self.routes)


app = MiniApp()


@app.post("/plan")
def create_plan(payload: Dict[str, Any]) -> Response:
    try:
        profile = UserProfile.from_dict(payload.get("profile", {}))
        goal = Goal.from_dict(payload.get("goal", {}))
    except Exception as exc:
        return Response({"error": str(exc)}, status_code=400)

    meals = plan_meals(profile, goal)
    workouts = plan_workouts(profile, goal)
    plan = DayPlan(user_id=profile.user_id, meals=meals, workouts=workouts)
    return Response(plan.to_dict())


@app.post("/schedule")
def schedule_day(payload: Dict[str, Any]) -> Response:
    try:
        req = ScheduleRequest.from_dict(payload)
    except Exception as exc:
        return Response({"error": str(exc)}, status_code=400)

    schedule = build_schedule(req)
    return Response(schedule.to_dict())


@app.post("/nudge")
def send_motivation(payload: Dict[str, Any]) -> Response:
    try:
        nudge_request = NudgeRequest.from_dict(payload)
    except Exception as exc:
        return Response({"error": str(exc)}, status_code=400)
    response = send_nudge(nudge_request)
    return Response(response.to_dict())


@app.post("/feedback")
def feedback(payload: Dict[str, Any]) -> Response:
    try:
        fb = Feedback.from_dict(payload)
    except Exception as exc:
        return Response({"error": str(exc)}, status_code=400)
    result = handle_feedback(fb)
    return Response(result)


@app.get("/")
def index(_: Dict[str, Any]) -> Response:
    return Response({"message": "Personal Health Coach API", "endpoints": list(app.routes.keys())})


if __name__ == "__main__":
    # Minimal HTTP server for manual exploration (no external deps)
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import json

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, response: Response):
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response.data).encode())

        def do_GET(self):
            handler = app.routes.get(("GET", self.path))
            if not handler:
                self._respond(Response({"error": "not found"}, status_code=404))
                return
            self._respond(handler({}))

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(body.decode() or "{}")
            except json.JSONDecodeError:
                payload = {}
            handler = app.routes.get(("POST", self.path))
            if not handler:
                self._respond(Response({"error": "not found"}, status_code=404))
                return
            self._respond(handler(payload))

    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Serving on http://0.0.0.0:8000")
    server.serve_forever()
