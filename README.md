# Seasonal Color Analysis (MVP Scaffold)

Monorepo scaffold for a deterministic CV-based seasonal color analysis app.

## Stack

- Web: Next.js 15 + TypeScript (`apps/web`)
- API + Worker: FastAPI + RQ + SQLAlchemy (`apps/api`)
- Storage/Infra: Postgres, Redis, MinIO (`infra/docker/docker-compose.yml`)
- Shared contracts: generated TypeScript definitions from OpenAPI (`packages/shared-types`)

## Quick Start

### Option A: Docker infra + local app processes

1. Start infrastructure:

```bash
cd infra/docker
docker compose up -d
```

2. Run API locally:

```bash
cd apps/api
python -m pip install -e '.[dev]'
uvicorn color_analysis.main:app --app-dir src --reload --port 8000
```

3. Run worker locally:

```bash
cd apps/api
python -m color_analysis.workers.main
```

4. Run web locally:

```bash
corepack pnpm install
corepack pnpm --filter @color-analysis/web dev
```

### Option B: Local macOS (no Docker)

Use this path if Docker/MinIO is unavailable locally.

1. Install and start local services:

```bash
brew install postgresql@18 redis
brew services start postgresql@18
brew services start redis
```

2. Create API venv + dependencies:

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pip install 'moto[server]==5.1.4'
```

3. Bootstrap Postgres and create API tables:

```bash
cd apps/api
. .venv/bin/activate
psql postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN CREATE ROLE postgres LOGIN PASSWORD 'postgres'; ELSE ALTER ROLE postgres WITH LOGIN PASSWORD 'postgres'; END IF; END \$\$;"
psql postgres -c "CREATE DATABASE color_analysis OWNER postgres;" 2>/dev/null || true
PYTHONPATH=src python - <<'PY'
import asyncio
from color_analysis.db.base import Base, engine
import color_analysis.db.models  # noqa: F401

async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())
PY
```

4. Run local S3-compatible storage and create bucket:

```bash
cd apps/api
. .venv/bin/activate
moto_server -H 127.0.0.1 -p 9000
```

In a separate terminal:

```bash
cd apps/api
. .venv/bin/activate
python -c "import boto3; s3=boto3.client('s3', endpoint_url='http://127.0.0.1:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin', region_name='us-east-1'); names=[b['Name'] for b in s3.list_buckets().get('Buckets', [])]; s3.create_bucket(Bucket='color-analysis') if 'color-analysis' not in names else None"
```

5. Run API:

```bash
cd apps/api
. .venv/bin/activate
export PYTHONPATH=src
export COLOR_ANALYSIS_POSTGRES_DSN='postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/color_analysis'
export COLOR_ANALYSIS_REDIS_URL='redis://127.0.0.1:6379/0'
export COLOR_ANALYSIS_S3_ENDPOINT_URL='http://127.0.0.1:9000'
export COLOR_ANALYSIS_S3_ACCESS_KEY_ID='minioadmin'
export COLOR_ANALYSIS_S3_SECRET_ACCESS_KEY='minioadmin'
export COLOR_ANALYSIS_S3_BUCKET='color-analysis'
uvicorn color_analysis.main:app --app-dir src --reload --port 8000
```

6. Run worker:

```bash
cd apps/api
. .venv/bin/activate
export PYTHONPATH=src
export COLOR_ANALYSIS_POSTGRES_DSN='postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/color_analysis'
export COLOR_ANALYSIS_REDIS_URL='redis://127.0.0.1:6379/0'
export COLOR_ANALYSIS_S3_ENDPOINT_URL='http://127.0.0.1:9000'
export COLOR_ANALYSIS_S3_ACCESS_KEY_ID='minioadmin'
export COLOR_ANALYSIS_S3_SECRET_ACCESS_KEY='minioadmin'
export COLOR_ANALYSIS_S3_BUCKET='color-analysis'
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
python -m color_analysis.workers.main
```

7. Run web:

```bash
cd ../..
corepack pnpm install
corepack pnpm --filter @color-analysis/web dev
```

## Troubleshooting: Can't Connect to Server

If the browser shows a connection error or analysis stays stuck on "Curating your profile", one of the local dev processes is usually not running.

One-command restart (recommended):

```bash
./scripts/restart-dev.sh
```

`restart-dev.sh` now starts infra + API + worker + web and writes logs to `${TMPDIR:-/tmp}/color-analysis`.

Stop all dev app processes without restarting:

```bash
./scripts/kill-dev.sh
```

Stop app processes and Docker infra services to fully quiet background usage:

```bash
./scripts/kill-dev.sh --with-infra
```

Start/restart all three app processes in separate terminals:

1. API (terminal 1):

```bash
cd apps/api
python -m pip install -e '.[dev]'  # first-time setup only
uvicorn color_analysis.main:app --app-dir src --port 8000
```

2. Worker (terminal 2):

```bash
cd apps/api
. .venv/bin/activate
export PYTHONPATH=src
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
python -m color_analysis.workers.main
```

3. Web (terminal 3):

```bash
corepack pnpm install  # first-time setup only
corepack pnpm --filter @color-analysis/web dev
```

Quick checks:

```bash
curl -sS http://127.0.0.1:8000/health
# expected: {"status":"ok"}

pgrep -fl "color_analysis.workers.main"
# expected: one running worker process
```

Open `http://localhost:3000` for the web UI.

## Troubleshooting: Known Startup Failures

1. API fails immediately with `ERROR: [Errno 1] Operation not permitted`:

This usually comes from `uvicorn --reload` in restricted environments where file watching is blocked.

Start API without reload:

```bash
cd apps/api
uvicorn color_analysis.main:app --app-dir src --port 8000
```

2. API startup fails with `EndpointConnectionError: Could not connect to the endpoint URL: "http://localhost:9000/color-analysis"`:

This means local infra (especially MinIO) is not reachable or not initialized.

Start infra services explicitly:

```bash
cd infra/docker
docker compose up -d postgres redis minio minio-init
```

3. `docker compose up -d` fails while building API/worker images with `error in 'egg_base' option: 'src' does not exist or is not a directory`:

For local app development, you do not need to build/run API or worker containers. Start infra-only services:

```bash
cd infra/docker
docker compose up -d postgres redis minio minio-init
```

Then run API/web locally from `apps/api` and `apps/web`.

4. Web fails with `Error: listen EPERM: operation not permitted 0.0.0.0:3000`:

This is typically an environment/sandbox permission issue around binding local ports.
Run the frontend from a normal local terminal session (outside restricted sandbox tooling) and retry:

```bash
corepack pnpm --filter @color-analysis/web dev
```

## Useful Commands

- Export OpenAPI:

```bash
cd apps/api
python scripts/export_openapi.py
```

- Build shared types:

```bash
pnpm --filter @color-analysis/shared-types build
```

- CV pipeline CLI on fixture photos:

```bash
cd apps/api
python -m color_analysis.cv tests/fixtures/happy_path
```

- Eval regression gate:

```bash
cd apps/api
python ../../eval/scripts/run_eval.py
python ../../eval/scripts/compare_eval.py
```

- Run TTL retention sweep manually:

```bash
cd apps/api
python -m color_analysis.workers.retention
```

## What is implemented now

- Monorepo scaffold and CI workflows
- FastAPI API routes for sessions, photos, analysis, status/result, admin trace
- Deterministic CV pipeline package with stage trace output
- RQ worker scaffold that runs analysis and persists result rows
- Alembic initial migration and SQLAlchemy models
- Retention/delete primitives via hard-delete and sweeper hooks
- Next.js flow: landing -> analyze -> result -> delete
- No-analyst eval baseline scripts (stability/robustness placeholder metrics)

## Notes

- This is a functional MVP scaffold, not production-hardened CV accuracy.
- The pipeline is deterministic and inspectable by design; model quality should improve via later tuning.
- No LLM is used in the measurement/classification path.
