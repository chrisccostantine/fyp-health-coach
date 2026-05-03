@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing Python virtual environment.
  echo Run: python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)

if not exist "health-coach-react\node_modules" (
  echo Missing frontend dependencies.
  echo Run: cd health-coach-react ^&^& npm install
  exit /b 1
)

start "Diet Agent 8101" cmd /k ".venv\Scripts\python.exe -m services.diet_agent.app"
start "Exercise Agent 8102" cmd /k ".venv\Scripts\python.exe -m services.exercise_agent.app"
start "Motivation Agent 8103" cmd /k ".venv\Scripts\python.exe -m services.motivation_agent.app"
start "Scheduler Agent 8104" cmd /k ".venv\Scripts\python.exe -m services.scheduler_agent.app"
start "Feedback Agent 8105" cmd /k ".venv\Scripts\python.exe -m services.feedback_agent.app"
start "Gateway 8000" cmd /k ".venv\Scripts\python.exe -m services.gateway.app"
start "React Frontend" cmd /k "cd /d health-coach-react && npm run dev"

echo Started Health Coach dev stack.
echo Gateway:  http://127.0.0.1:8000
echo Frontend: check the React Frontend window for the Vite URL.
pause
