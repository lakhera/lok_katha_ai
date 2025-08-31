#!/bin/bash
set -e

# Activate venv if exists
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

# Install deps if needed
pip install -r requirements.txt

# Run app
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
