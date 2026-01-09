import requests, json

G = "http://127.0.0.1:8000"

print("\n== Plan today ==")
plan = requests.post(f"{G}/plan/today", json={
    "user_id":"demo-user",
    "profile":{"age":24,"sex":"M","height_cm":178,"weight_kg":78,"activity_level":"moderate"},
    "goal":{"type":"fat_loss","deficit_kcal":400},
    "equipment":["dumbbells","pullup_bar"]
}).json()
print(json.dumps(plan, indent=2))

print("\n== Schedule commit ==")
ev = []
for m in plan["meals"]:
    ev.append({"type":"meal","name":m["name"],"scheduled_at":"2025-10-16T08:00:00","duration_min":15})
for w in plan["workouts"]:
    ev.append({"type":"workout","name":w["name"],"scheduled_at":"2025-10-16T18:00:00","duration_min":w["duration_min"]})
sch = requests.post(f"{G}/schedule/commit", json={"user_id":"demo-user","events":ev}).json()
print(json.dumps(sch, indent=2))

print("\n== Nudge send ==")
ndg = requests.post(f"{G}/nudge/send", json={"user_id":"demo-user","tone":"coach","goal":"stay_consistent"}).json()
print(json.dumps(ndg, indent=2))

print("\n== Feedback (5 stars on first event) ==")
eid = sch["events"][0]["id"]
fb = requests.post(f"{G}/feedback", json={"event_id": eid, "user_id":"demo-user", "rating":5, "reason":"felt great", "bandit_arm":"coach"}).json()
print(json.dumps(fb, indent=2))
