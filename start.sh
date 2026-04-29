#!/usr/bin/env bash
set -euo pipefail

cleanup() {
  jobs -p | xargs -r kill
}

trap cleanup EXIT INT TERM

python -m services.diet_agent.app &
python -m services.exercise_agent.app &
python -m services.motivation_agent.app &
python -m services.scheduler_agent.app &
python -m services.feedback_agent.app &
python -m services.gateway.app &

wait -n
