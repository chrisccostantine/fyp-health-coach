# FYP Health Coach

This project is a multi-agent personal health coach with:

- a Flask gateway API
- five backend agents: diet, exercise, motivation, scheduler, and feedback
- a React + Vite frontend in `health-coach-react`

The backend can run without OpenAI keys by falling back to rule-based responses.

## Project Structure

- `services/gateway` - main API entrypoint on port `8000`
- `services/diet_agent` - diet planning agent on port `8101`
- `services/exercise_agent` - exercise planning agent on port `8102`
- `services/motivation_agent` - motivation agent on port `8103`
- `services/scheduler_agent` - scheduling agent on port `8104`
- `services/feedback_agent` - feedback agent on port `8105`
- `services/common` - shared models and SQLite storage helper
- `health-coach-react` - React frontend
- `scripts` - helper scripts such as demo data and API flow testing
- `tests` - integration test that hits running backend services

## Requirements

- Python 3.10+
- Node.js 18+ and npm

## Backend Setup

Create a virtual environment and install the Python dependencies:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` and `services/requirements.all.txt` currently contain the backend dependencies used by the services.

## Environment Variables

### Gateway URLs

Create a root `.env` file from `.env.example` if you want to override service URLs:

```powershell
Copy-Item .env.example .env
```

Default local URLs are:

- `DIET_URL=http://127.0.0.1:8101`
- `EXERCISE_URL=http://127.0.0.1:8102`
- `MOTIVATION_URL=http://127.0.0.1:8103`
- `SCHEDULER_URL=http://127.0.0.1:8104`
- `FEEDBACK_URL=http://127.0.0.1:8105`

### Optional OpenAI Keys

If you want AI-backed diet or exercise chat/planning, create these files:

```powershell
Copy-Item services\diet_agent\diet.env.example services\diet_agent\diet.env
Copy-Item services\exercise_agent\exercise.env.example services\exercise_agent\exercise.env
```

Then put your API key in each file:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

If those files are missing or the key is empty, the app still runs with rule-based logic.

## Run the Backend

Start each service in its own terminal:

```powershell
python -m services.diet_agent.app
python -m services.exercise_agent.app
python -m services.motivation_agent.app
python -m services.scheduler_agent.app
python -m services.feedback_agent.app
python -m services.gateway.app
```

Or use the helper script after activating the virtual environment:

```powershell
run_all.bat
```

Backend ports:

- Gateway: `8000`
- Diet Agent: `8101`
- Exercise Agent: `8102`
- Motivation Agent: `8103`
- Scheduler Agent: `8104`
- Feedback Agent: `8105`

Quick health check:

```powershell
curl http://127.0.0.1:8000/health
```

## Run the Frontend

Install frontend dependencies:

```powershell
cd health-coach-react
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend is configured to call the gateway at `http://127.0.0.1:8000` by default.

## Run Everything From Scratch

Backend:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python -m services.diet_agent.app
python -m services.exercise_agent.app
python -m services.motivation_agent.app
python -m services.scheduler_agent.app
python -m services.feedback_agent.app
python -m services.gateway.app
```

Frontend:

```powershell
cd health-coach-react
npm install
npm run dev
```

## Useful API Endpoints

- `GET /health` - gateway health check
- `POST /plan/today` - combine diet and exercise suggestions into one day plan
- `POST /schedule/commit` - schedule events
- `POST /nudge/send` - generate a motivation message
- `POST /feedback` - submit event feedback
- `POST /diet/chat` - modify diet plan via the diet agent

Example `POST /plan/today` request:

```json
{
  "user_id": "demo-user",
  "profile": {
    "age": 24,
    "sex": "M",
    "height_cm": 178,
    "weight_kg": 78,
    "activity_level": "moderate"
  },
  "goal": {
    "type": "fat_loss",
    "deficit_kcal": 400
  },
  "equipment": ["dumbbells", "pullup_bar"]
}
```

## Demo Scripts

Seed demo data:

```powershell
python scripts\seed.py
```

Run the sample API flow:

```powershell
python scripts\demo_flow.py
```

## Tests

The integration test expects the backend services to already be running:

```powershell
pytest tests\test_integration.py
```

## Storage

- SQLite database path: `storage/app.db`
- This file is generated locally and is ignored by Git

## Notes

- If you recreated the virtual environment, rerun `pip install -r requirements.txt`
- If the frontend cannot reach the backend, make sure the gateway is running on port `8000`
- If AI responses are not working, confirm the `diet.env` and `exercise.env` files contain a valid `OPENAI_API_KEY`
