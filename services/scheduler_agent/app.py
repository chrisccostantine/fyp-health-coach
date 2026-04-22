from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# In-memory schedule (replace with Google Calendar later)
SCHEDULE = {}

@app.post("/schedule/commit")
def commit():
    body = request.get_json(force=True)
    # Expect: { user_id, events: [ {type, name, scheduled_at, duration_min} ] }
    user_id = body.get("user_id","anon")
    events = body.get("events", [])
    saved = []
    for e in events:
        eid = str(uuid.uuid4())
        item = {"id": eid, **e}
        SCHEDULE.setdefault(user_id, []).append(item)
        saved.append(item)
    return jsonify({"ok": True, "events": saved})

@app.get("/schedule/list")
def list_events():
    user_id = (request.args.get("user_id") or "anon")
    return jsonify({"events": SCHEDULE.get(user_id,[])})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8104, debug=True)
