from flask import Flask, request, jsonify
import random
from services.common.storage import init_db, get_arms, upsert_arm, record_feedback

app = Flask(__name__)
init_db()

AGENT_NAME = "motivation_tone"
ARMS = ["coach","friendly"]
EPSILON = 0.2

# Ensure arms exist
for arm in ARMS:
    upsert_arm(AGENT_NAME, arm)

@app.get("/bandit/choose")
def choose():
    # epsilon-greedy on average reward
    arms = get_arms(AGENT_NAME)
    if random.random() < EPSILON:
        choice = random.choice(ARMS)
    else:
        # pick arm with best mean reward (default 0)
        best, best_mu = ARMS[0], -1e9
        for a in arms:
            pulls = a["pulls"] or 0
            mu = (a["reward_sum"] / pulls) if pulls > 0 else 0.0
            if mu > best_mu:
                best, best_mu = a["arm"], mu
        choice = best
    upsert_arm(AGENT_NAME, choice, pulled=True)
    return jsonify({"arm": choice, "epsilon": EPSILON})

@app.post("/feedback")
def feedback():
    body = request.get_json(force=True)
    # Expect: {event_id, user_id, rating, reason, bandit_arm?}
    event_id = body.get("event_id","")
    user_id = body.get("user_id","anon")
    rating = int(body.get("rating",3))
    reason = body.get("reason")
    arm = body.get("bandit_arm")
    record_feedback(event_id, user_id, rating, reason)
    if arm in ARMS:
        reward = max(0.0, (rating - 3) / 2.0)  # map 1..5 -> -1..+1 -> clamp to 0..1
        upsert_arm(AGENT_NAME, arm, reward=reward)
    return jsonify({"ok": True, "logged": {"event_id":event_id, "rating":rating, "reason":reason, "arm":arm}})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8105, debug=True)
