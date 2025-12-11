#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root based on this script's location
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---- Config: adjust if your commands/paths differ ----
VENV_PATH="$ROOT_DIR/.venv"
BACKEND_DIR="$ROOT_DIR/apps/API"
BACKEND_CMD="uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

# If your frontend dev command is different, change this line only.
FRONTEND_CMD="npm run dev -w @app/web"
# e.g. could be:
# FRONTEND_CMD="npm run dev -w @app/web"
# or: FRONTEND_CMD="pnpm dev --dir apps/web"

# ------------------------------------------------------

echo "Repo root: $ROOT_DIR"

# Activate venv if present
if [ -f "$VENV_PATH/bin/activate" ]; then
  echo "Activating virtualenv at $VENV_PATH"
  # shellcheck source=/dev/null
  source "$VENV_PATH/bin/activate"
else
  echo "WARNING: No virtualenv found at $VENV_PATH"
fi

# Start backend
echo "Starting backend in $BACKEND_DIR ..."
cd "$BACKEND_DIR"

# .env.local in apps/API will be picked up by your Settings class
$BACKEND_CMD &
API_PID=$!
echo "Backend started with PID $API_PID"

# Ensure backend gets killed when we exit
cleanup() {
  echo
  echo "Shutting down backend (PID $API_PID)..."
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start frontend (foreground)
echo "Starting frontend from $ROOT_DIR ..."
cd "$ROOT_DIR"
echo "Running: $FRONTEND_CMD"
$FRONTEND_CMD
