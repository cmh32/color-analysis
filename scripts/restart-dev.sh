#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${TMPDIR:-/tmp}/color-analysis"
API_LOG="$LOG_DIR/api.log"
WEB_LOG="$LOG_DIR/web.log"
WORKER_LOG="$LOG_DIR/worker.log"
API_PID_FILE="$LOG_DIR/api.pid"
WEB_PID_FILE="$LOG_DIR/web.pid"
WORKER_PID_FILE="$LOG_DIR/worker.pid"

mkdir -p "$LOG_DIR"

detect_lan_ip() {
  local ip
  ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$ip" ]]; then
    ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  echo "$ip"
}

LAN_IP="$(detect_lan_ip)"
LAN_WEB_URL=""
LAN_API_URL=""

if [[ -n "$LAN_IP" ]]; then
  LAN_WEB_URL="http://${LAN_IP}:3000"
  LAN_API_URL="http://${LAN_IP}:8000"
fi

CORS_ALLOWED_ORIGINS_JSON='["http://localhost:3000","http://127.0.0.1:3000"'
if [[ -n "$LAN_WEB_URL" ]]; then
  CORS_ALLOWED_ORIGINS_JSON+=",\"${LAN_WEB_URL}\""
fi
CORS_ALLOWED_ORIGINS_JSON+="]"

kill_listeners_on_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  echo "Stopping listeners on port ${port}: ${pids}"
  kill $pids 2>/dev/null || true
  sleep 1

  local survivors
  survivors="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$survivors" ]]; then
    echo "Force stopping remaining listeners on port ${port}: ${survivors}"
    kill -9 $survivors 2>/dev/null || true
  fi
}

kill_processes_matching() {
  local pattern="$1"
  local pids
  pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  echo "Stopping processes matching '${pattern}': ${pids}"
  kill $pids 2>/dev/null || true
  sleep 1

  local survivors
  survivors="$(pgrep -f "$pattern" 2>/dev/null || true)"
  if [[ -n "$survivors" ]]; then
    echo "Force stopping remaining processes matching '${pattern}': ${survivors}"
    kill -9 $survivors 2>/dev/null || true
  fi
}

wait_for_http() {
  local url="$1"
  local expected="$2"
  local label="$3"
  local attempts=30
  local i=0

  while (( i < attempts )); do
    local code
    code="$(curl -sS -o /dev/null -m 2 -w "%{http_code}" "$url" 2>/dev/null || true)"
    if [[ "$code" == "$expected" ]]; then
      echo "${label} is ready (${url} -> ${code})"
      return 0
    fi
    sleep 1
    ((i+=1))
  done

  echo "${label} failed readiness check at ${url} (expected ${expected})"
  return 1
}

wait_for_health_json() {
  local url="$1"
  local attempts=30
  local i=0

  while (( i < attempts )); do
    local body
    body="$(curl -sS -m 2 "$url" 2>/dev/null || true)"
    if [[ "$body" == '{"status":"ok"}' ]]; then
      echo "API health is ready (${url} -> ${body})"
      return 0
    fi
    sleep 1
    ((i+=1))
  done

  echo "API health failed readiness check at ${url}"
  return 1
}

echo "Restarting local dev stack..."

kill_listeners_on_port 8000
kill_listeners_on_port 3000
kill_processes_matching "color_analysis.workers.main"

echo "Starting infra services (postgres, redis, minio, minio-init)..."
(
  cd "$ROOT_DIR/infra/docker"
  docker compose up -d postgres redis minio minio-init
)

if [[ ! -x "$ROOT_DIR/apps/api/.venv/bin/uvicorn" ]]; then
  echo "Missing API venv executable at apps/api/.venv/bin/uvicorn"
  echo "Run: cd apps/api && python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'"
  exit 1
fi

if [[ ! -d "$ROOT_DIR/node_modules" ]]; then
  echo "Installing Node dependencies..."
  (
    cd "$ROOT_DIR"
    corepack pnpm install
  )
fi

echo "Starting API (no --reload) on port 8000..."
(
  cd "$ROOT_DIR/apps/api"
  nohup env COLOR_ANALYSIS_CORS_ALLOWED_ORIGINS="$CORS_ALLOWED_ORIGINS_JSON" .venv/bin/uvicorn color_analysis.main:app --app-dir src --host 0.0.0.0 --port 8000 >"$API_LOG" 2>&1 &
  echo $! >"$API_PID_FILE"
)

echo "Starting worker..."
(
  cd "$ROOT_DIR/apps/api"
  nohup zsh -lc '. .venv/bin/activate; export PYTHONPATH=src; export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES; python -m color_analysis.workers.main' >"$WORKER_LOG" 2>&1 &
  echo $! >"$WORKER_PID_FILE"
)

echo "Starting web on port 3000..."
(
  cd "$ROOT_DIR"
  if [[ -n "$LAN_API_URL" ]]; then
    nohup env NEXT_PUBLIC_API_BASE_URL="$LAN_API_URL" corepack pnpm --filter @color-analysis/web dev >"$WEB_LOG" 2>&1 &
  else
    nohup corepack pnpm --filter @color-analysis/web dev >"$WEB_LOG" 2>&1 &
  fi
  echo $! >"$WEB_PID_FILE"
)

wait_for_health_json "http://127.0.0.1:8000/health"
wait_for_http "http://127.0.0.1:3000" "200" "Web"

echo "Restart complete."
echo "API log: $API_LOG"
echo "Web log: $WEB_LOG"
echo "Worker log: $WORKER_LOG"
echo "API pid: $(cat "$API_PID_FILE")"
echo "Web pid: $(cat "$WEB_PID_FILE")"
echo "Worker pid: $(cat "$WORKER_PID_FILE")"
echo "Web URL (local): http://localhost:3000"
echo "API URL (local): http://127.0.0.1:8000"
if [[ -n "$LAN_WEB_URL" ]]; then
  echo "Web URL (LAN): $LAN_WEB_URL"
  echo "API URL (LAN): $LAN_API_URL"
fi
