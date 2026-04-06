#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
AUTO_OPEN_BROWSER="${AUTO_OPEN_BROWSER:-1}"

export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${API_PORT}}"
export NEXT_PUBLIC_WS_BASE_URL="${NEXT_PUBLIC_WS_BASE_URL:-ws://localhost:${API_PORT}}"

API_PID=""
WEB_PID=""

cleanup() {
  if [[ -n "${WEB_PID}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required"
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/apps/web/node_modules" ]] && [[ ! -d "${ROOT_DIR}/node_modules" ]]; then
  echo "frontend dependencies are missing. Run: npm install"
  exit 1
fi

echo "Starting API on ${API_HOST}:${API_PORT}"
(
  cd "${ROOT_DIR}"
  API_HOST="${API_HOST}" API_PORT="${API_PORT}" python3 apps/api/run.py
) &
API_PID=$!

sleep 1

echo "Starting web on 0.0.0.0:${WEB_PORT}"
(
  cd "${ROOT_DIR}/apps/web"
  PORT="${WEB_PORT}" npm run dev
) &
WEB_PID=$!

echo "Web: http://localhost:${WEB_PORT}"
echo "API: http://localhost:${API_PORT}"
echo "Open the game in your browser at http://localhost:${WEB_PORT}"
echo "The API is not the game page. http://localhost:${API_PORT} is backend only."
echo "Press Ctrl+C to stop both processes"

if [[ "${AUTO_OPEN_BROWSER}" == "1" ]] && command -v xdg-open >/dev/null 2>&1; then
  (
    sleep 2
    xdg-open "http://localhost:${WEB_PORT}" >/dev/null 2>&1 || true
  ) &
fi

wait "${API_PID}" "${WEB_PID}"
