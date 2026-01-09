from flask import Flask, request, jsonify

app = Flask(__name__)

TONES = {
    "coach": [
        "Small wins stack up. Show up for just 10 minutes—momentum will do the rest.",
        "You don’t need perfect. You need consistent. Let’s get one rep closer.",
        "Future you is watching. Give them something to be proud of today."
    ],
    "friendly": [
        "You’ve got this! A little movement now makes the whole day better.",
        "Let’s knock out one healthy choice—right now. I’m with you.",
        "Quick reminder: you deserve to feel awesome. One step today!"
    ]
}

@app.post("/nudge/send")
def nudge():
    body = request.get_json(force=True)
    tone = body.get("tone","coach")
    msg = TONES.get(tone, TONES["coach"])[0]
    return jsonify({"message": msg, "tone": tone})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8103, debug=True)
