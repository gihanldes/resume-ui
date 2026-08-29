#!/usr/bin/env bash
# Start the API on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
