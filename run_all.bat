@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate

start "Diet Agent" cmd /k python -m services.diet_agent.app
start "Exercise Agent" cmd /k python -m services.exercise_agent.app
start "Motivation Agent" cmd /k python -m services.motivation_agent.app
start "Scheduler Agent" cmd /k python -m services.scheduler_agent.app
start "Feedback Agent" cmd /k python -m services.feedback_agent.app
start "Gateway" cmd /k python -m services.gateway.app

echo Started all services (ports: 8101..8105, gateway 8000).
pause
