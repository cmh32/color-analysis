#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${TMPDIR:-/tmp}/color-analysis"
API_PID_FILE="$LOG_DIR/api.pid"
WEB_PID_FILE="$LOG_DIR/web.pid"
WORKER_PID_FILE="$LOG_DIR/worker.pid"
WITH_INFRA=false

mkdir -p "$LOG_DIR"

usage() {
  cat <<'EOF'
Usage: ./scripts/kill-dev.sh [--with-infra]

Options:
  --with-infra   Also stop local Docker infra services (postgres, redis, minio, minio-init).
  -h, --help     Show this help message.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --with-infra)
      WITH_INFRA=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage
      exit 1
      ;;
  esac
done

stop_pid() {
  local pid="$1"
  local label="$2"

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "${label} pid ${pid} is not running."
    return 0
  fi

  echo "Stopping ${label} pid ${pid}..."
  kill "$pid" 2>/dev/null || true

  local i
  for i in {1..10}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "${label} stopped."
      return 0
    fi
    sleep 0.3
  done

  echo "Force stopping ${label} pid ${pid}..."
  kill -9 "$pid" 2>/dev/null || true
}

stop_from_pid_file() {
  local file="$1"
  local label="$2"

  if [[ ! -f "$file" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]]; then
    stop_pid "$pid" "$label"
  fi
}

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

stop_infra_services() {
  local compose_dir="$ROOT_DIR/infra/docker"
  if [[ ! -d "$compose_dir" ]]; then
    echo "Skipping infra shutdown: missing directory $compose_dir"
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "Skipping infra shutdown: docker is not installed."
    return 0
  fi

  echo "Stopping infra services (postgres, redis, minio, minio-init)..."
  if ! (cd "$compose_dir" && docker compose stop postgres redis minio minio-init); then
    echo "Infra shutdown failed. Ensure Docker is running and retry." >&2
    return 1
  fi
}

echo "Stopping local dev processes..."

stop_from_pid_file "$API_PID_FILE" "API"
stop_from_pid_file "$WEB_PID_FILE" "Web"
stop_from_pid_file "$WORKER_PID_FILE" "Worker"

# Fallback cleanup for stale PID files or detached processes.
kill_listeners_on_port 8000
kill_listeners_on_port 3000
kill_processes_matching "color_analysis.workers.main"

rm -f "$API_PID_FILE" "$WEB_PID_FILE" "$WORKER_PID_FILE"

if [[ "$WITH_INFRA" == true ]]; then
  stop_infra_services
fi

echo "Dev processes stopped."
