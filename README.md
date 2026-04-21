# Seasonal Color Analysis

Monorepo for a deterministic CV-based seasonal color analysis app.

## Stack

- Web: Next.js 15 + TypeScript in `apps/web`
- API: FastAPI + SQLAlchemy in `apps/api`
- Worker: RQ worker in `apps/api`
- Infra: Postgres, Redis, and MinIO via Docker Compose in `infra/docker`
- Shared contracts: generated TypeScript definitions in `packages/shared-types`

## Default Startup Protocol

The default local startup path is:

```bash
./scripts/restart-dev.sh
```

That is the best day-to-day entrypoint for this repo because it does the full local orchestration in one place:

- stops stale API, worker, and web processes
- starts Docker infra services: Postgres, Redis, MinIO, and bucket init
- starts the API on `:8000`
- starts the worker
- starts the web app on `:3000`
- waits for API and web readiness checks before returning
- writes logs and PID files under `${TMPDIR:-/tmp}/color-analysis`

Use manual per-service startup only when you are debugging a specific process.

## First-Time Setup

### Prerequisites

- Docker Desktop, with Docker running
- Python `3.12`
- Node.js with `corepack`

### Bootstrap once

1. Install workspace dependencies:

```bash
corepack pnpm install
```

2. Create the API virtualenv and install API dependencies:

```bash
cd apps/api
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cd ../..
```

3. Start the full dev stack:

```bash
./scripts/restart-dev.sh
```

4. Open the app:

```text
http://localhost:3000
```

If you want to test from another device on your LAN, `restart-dev.sh` also detects a local IP and wires the web app to the API using that address when possible.

## Daily Development

From the repo root, use the restart script whenever you want a clean local stack:

```bash
./scripts/restart-dev.sh
```

This should be the normal workflow after the one-time bootstrap above.

### Stop processes

Stop API, worker, and web:

```bash
./scripts/kill-dev.sh
```

Stop app processes and Docker infra:

```bash
./scripts/kill-dev.sh --with-infra
```

### Check health

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Inspect logs

```bash
tail -f "${TMPDIR:-/tmp}/color-analysis/api.log"
tail -f "${TMPDIR:-/tmp}/color-analysis/worker.log"
tail -f "${TMPDIR:-/tmp}/color-analysis/web.log"
```

## Why This Is The Default

`./scripts/restart-dev.sh` is a better default than `pnpm dev` or starting services manually because this app needs more than a single frontend process:

- the web app depends on the API
- analysis work depends on the worker
- both API and worker depend on Postgres, Redis, and MinIO
- the script uses a stable non-reload API launch, which avoids the local file-watcher issues already seen with `uvicorn --reload`

`pnpm dev` is still useful for narrower frontend-only work, but it is not the best default for getting the full application running.

## Manual Fallback Startup

Use this only if `restart-dev.sh` fails or you need to isolate one service.

1. Start infra:

```bash
cd infra/docker
docker compose up -d postgres redis minio minio-init
cd ../..
```

2. Start the API:

```bash
cd apps/api
. .venv/bin/activate
uvicorn color_analysis.main:app --app-dir src --host 0.0.0.0 --port 8000
```

3. Start the worker in a second terminal:

```bash
cd apps/api
. .venv/bin/activate
export PYTHONPATH=src
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
python -m color_analysis.workers.main
```

4. Start the web app in a third terminal:

```bash
corepack pnpm --filter @color-analysis/web dev
```

## Common Startup Failures

### `apps/api/.venv/bin/uvicorn` is missing

The restart script expects the API virtualenv to already exist.

```bash
cd apps/api
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

### Docker infra does not come up

Make sure Docker Desktop is running, then retry:

```bash
cd infra/docker
docker compose up -d postgres redis minio minio-init
```

### API fails with file-watch or permission errors

The recommended script already avoids `--reload`, which is why it is the preferred startup path. If you start the API manually, use:

```bash
cd apps/api
. .venv/bin/activate
uvicorn color_analysis.main:app --app-dir src --host 0.0.0.0 --port 8000
```

### Web loads but analysis stalls

Usually one of the backend processes is down. Re-run:

```bash
./scripts/restart-dev.sh
```
