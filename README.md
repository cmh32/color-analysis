# Seasonal Color Analysis (MVP Scaffold)

Monorepo scaffold for a deterministic CV-based seasonal color analysis app.

## Stack

- Web: Next.js 15 + TypeScript (`apps/web`)
- API + Worker: FastAPI + RQ + SQLAlchemy (`apps/api`)
- Storage/Infra: Postgres, Redis, MinIO (`infra/docker/docker-compose.yml`)
- Shared contracts: generated TypeScript definitions from OpenAPI (`packages/shared-types`)

## Quick Start

1. Start infrastructure:

```bash
cd infra/docker
docker compose up -d
```

2. Run API locally:

```bash
cd apps/api
python -m pip install -e .[dev]
uvicorn color_analysis.main:app --app-dir src --reload --port 8000
```

3. Run worker locally:

```bash
cd apps/api
python -m color_analysis.workers.main
```

4. Run web locally:

```bash
pnpm install
pnpm --filter @color-analysis/web dev
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
