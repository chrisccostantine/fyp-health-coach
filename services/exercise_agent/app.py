from flask import Flask, request, jsonify

app = Flask(__name__)

WORKOUTS = {
    "fat_loss": [
        {"name":"Full-Body Circuit (No Machines)", "duration_min":30, "intensity":"high", "when":"18:00"},
        {"name":"Incline Walk + Core", "duration_min":25, "intensity":"medium", "when":"07:00"}
    ],
    "muscle_gain": [
        {"name":"Upper Push (DB/Bench)", "duration_min":45, "intensity":"medium", "when":"18:00"},
        {"name":"Lower Body (DB/Bodyweight)", "duration_min":40, "intensity":"medium", "when":"08:00"}
    ],
    "endurance": [
        {"name":"Tempo Run", "duration_min":35, "intensity":"medium", "when":"18:30"},
        {"name":"Zone 2 Ride", "duration_min":50, "intensity":"low", "when":"07:30"}
    ],
    "general_health": [
        {"name":"Brisk Walk + Mobility", "duration_min":30, "intensity":"low", "when":"19:00"}
    ]
}

@app.post("/exercise/suggest")
def suggest():
    body = request.get_json(force=True)
    goal = (body.get("goal") or {}).get("type","general_health")
    workouts = WORKOUTS.get(goal, WORKOUTS["general_health"])
    # Filter by equipment (MVP: just pass-through)
    return jsonify({"workouts": workouts})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8102, debug=True)
