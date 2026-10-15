# Flagpole — Feature Flag Management Platform

[![CI](https://github.com/YOUR_USERNAME/feature-flag-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/feature-flag-platform/actions/workflows/ci.yml)

A full-stack feature flag platform that lets teams turn features on and off in production, target specific users, and roll changes out gradually (1% → 10% → 100%) without redeploying.

**Stack:** FastAPI · PostgreSQL · Redis · React · Docker · GitHub Actions

---

## Why feature flags?

Shipping code and releasing a feature are two different things. With a flag, new code goes to production switched off; the team then opens it to internal testers, then to 5% of users, watches the metrics, and either keeps going or hits the kill switch. No redeploy, no rollback.

## Architecture

```mermaid
flowchart TB
    D[React dashboard<br/><small>create / toggle / target flags</small>] --> B
    C[Your app via SDK<br/><small>"is this flag on for me?"</small>] --> B
    B[FastAPI backend] -->|checked first| R[(Redis<br/><small>hot cache</small>)]
    B -->|only on cache miss| P[(PostgreSQL<br/><small>source of truth</small>)]
```

The backend is layered so each layer has exactly one reason to change:

| Layer | Folder | Responsibility |
|---|---|---|
| Routers | `app/routers/` | HTTP: parse and validate requests, return status codes |
| Services | `app/services/` | Business rules: evaluation order, versioning, cache invalidation |
| Engine | `app/services/engine.py` | Pure evaluation logic and hashing, no I/O, fully unit-tested |
| Repositories | `app/repositories/` | The only code that talks to PostgreSQL |
| Cache | `app/cache.py` | The only code that talks to Redis |

## The hot path: `GET /api/v1/evaluate`

Every SDK call hits this endpoint, so it is built to avoid PostgreSQL almost always.

```mermaid
flowchart LR
    A[1. Per-user eval cache] -- hit --> X([return])
    A -- miss --> B[2. Flag-definition cache]
    B -- hit --> D
    B -- miss --> C[3. PostgreSQL read<br/>repopulates cache]
    C --> D[4. Evaluate + MD5 bucket]
    D -- cache result --> A
```

Evaluation precedence for an enabled flag:

1. **Kill switch** — flag disabled → `OFF` for everyone
2. **Always-on users** — explicit user IDs (QA, internal testers)
3. **Targeting rules** — attribute rules such as `country equals IN` or `plan in [pro, enterprise]`
4. **Percentage rollout** — deterministic hash bucket

### The rollout hash

```
bucket = int(MD5("new-checkout:user_42"), 16) % 100     → 0..99
enabled = bucket < rollout_percentage
```

* **Deterministic:** the same user always gets the same answer, so nobody flickers between old and new UI on refresh.
* **Monotonic:** moving 20% → 50% only *adds* users. Anyone who already had the feature keeps it (bucket < 20 implies bucket < 50).
* **Independent per flag:** the flag key is part of the hash input, so the same 10% of users don't end up in every 10% experiment.
* **Uniform:** tested across 20,000 users; observed rollout stays within ±1.5 percentage points of target.

MD5 is used for speed and even distribution, not security (`usedforsecurity=False`).

## Measured latency

`python backend/scripts/benchmark.py` against a single uvicorn worker on PostgreSQL 16 + Redis 7. End-to-end HTTP round trip, measured from the client:

| Path | p50 | p95 | p99 |
|---|---|---|---|
| PostgreSQL read (Redis flushed every request) | 6.96 ms | 10.03 ms | 14.33 ms |
| Flag-definition cache hit | 3.52 ms | 5.56 ms | 7.48 ms |
| Per-user evaluation cache hit | **2.75 ms** | 3.99 ms | 5.40 ms |

Numbers will vary by machine; rerun the script to reproduce.

## Reliability engineering

Problems found while building this and how they're handled:

| Problem | Fix | Test |
|---|---|---|
| Toggling a flag left stale per-user results in Redis until TTL expiry. Deleting them needs a `SCAN` over millions of keys. | Every flag carries a **version**. Evaluation cache keys embed it (`eval:{key}:v{ver}:…`). A write bumps the version, so every old key becomes unreachable in O(1). | `test_toggle_invalidates_cached_evaluations` |
| Race: a slow request reads the old flag from Postgres, an admin updates it, then the slow request writes the old definition back into Redis. | `set_flag` uses `WATCH` on the version key and refuses to overwrite a newer version. | `test_stale_snapshot_does_not_overwrite_newer_version` |
| Lookups for unknown flags (typos in SDK calls) went to Postgres every time. | Short-lived **negative cache** (`flagmiss:{key}`, 10 s). | `test_unknown_flag_returns_404` |
| …which then hid a newly created flag behind a cached "not found". | Creating a flag clears its negative-cache entry. | `test_flag_created_after_negative_cache_is_visible_immediately` |
| Redis outage made every evaluation hang or crash with a 500. | All cache calls **fail open** to Postgres, with 250 ms socket timeouts and a 5 s cooldown so a dead Redis isn't retried on every request. `/health` reports `degraded`. | `test_redis_outage_falls_back_to_postgres` |
| Bad rule input (`age gt "abc"`) raised `ValueError` inside evaluation. | Numeric operators return "no match" on non-numeric input. | `test_rule_operators` |
| Stale pooled connections after a Postgres restart. | `pool_pre_ping=True` and `pool_recycle`. | — |
| Duplicate keys created under concurrent requests. | Unique index plus `IntegrityError` → `409 Conflict`. | `test_duplicate_key_returns_409` |

## Features

* Create, edit, toggle and delete flags from the dashboard
* Kill switch, always-on user list, attribute targeting rules, percentage rollout
* Live "test evaluation" panel showing the user's bucket against the cutoff
* Audit history of every change (e.g. rollout 20% → 50%, with timestamp)
* Batch evaluation endpoint for loading all flags on app start
* Health endpoint reporting database and cache status
* Dependency-free Python SDK that fails safe to a default value

## Running it

### With Docker (recommended)

```bash
docker compose up --build
python backend/scripts/seed.py      # optional demo flags (pip install httpx)
```

* Dashboard: http://localhost:3000
* API docs (Swagger): http://localhost:8000/docs

### Locally for development

```bash
docker compose up -d postgres redis

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev                          # http://localhost:5173
```

### Tests

```bash
cd backend
pytest                               # SQLite + fakeredis, no services needed

# against real services, as CI does
DATABASE_URL=postgresql+psycopg://flags:flags@localhost:5432/flags \
TEST_REDIS_URL=redis://localhost:6379/1 pytest
```

50 tests cover the hashing engine, rule operators, cache behaviour, the admin API and the evaluation API.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/flags` | List flags |
| `POST` | `/api/v1/flags` | Create flag |
| `GET` | `/api/v1/flags/{key}` | Get flag |
| `PATCH` | `/api/v1/flags/{key}` | Update fields (bumps version) |
| `POST` | `/api/v1/flags/{key}/toggle` | Flip the kill switch |
| `DELETE` | `/api/v1/flags/{key}` | Delete flag |
| `GET` | `/api/v1/evaluate?flag_key=&user_id=` | Evaluate one flag |
| `POST` | `/api/v1/evaluate` | Evaluate with user attributes |
| `POST` | `/api/v1/evaluate/batch` | Evaluate many flags for one user |
| `GET` | `/api/v1/audit?flag_key=` | Change history |
| `GET` | `/health` | Database and Redis status |

Example:

```bash
curl -X POST localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"flag_key":"upi-autopay","user_id":"user_42","attributes":{"country":"IN"}}'
```

```json
{"flag_key":"upi-autopay","user_id":"user_42","enabled":true,"reason":"RULE_MATCH",
 "bucket":null,"flag_version":1,"cached":false}
```

### SDK

```python
from flagpole import FlagClient

flags = FlagClient("http://localhost:8000")
if flags.is_enabled("new-checkout", user_id="user_42", attributes={"country": "IN"}):
    ...
```

## CI/CD

`.github/workflows/ci.yml` runs on every push and pull request:

1. **Backend** — `ruff` lint and format check, then `pytest` against real PostgreSQL 16 and Redis 7 service containers
2. **Frontend** — `npm ci` and production build
3. **Integration** — builds the full stack with Docker Compose, waits for health checks, seeds data and evaluates a flag through nginx
4. **Publish** — on `main`, pushes backend and frontend images to GitHub Container Registry

## Project structure

```
backend/
  app/
    routers/        HTTP layer
    services/       evaluation + admin logic, pure engine
    repositories/   PostgreSQL access
    cache.py        Redis access, versioned keys, fail-open
    models.py       SQLAlchemy models
    schemas.py      Pydantic request/response models
  tests/            50 tests
  scripts/          seed + benchmark
frontend/           React (Vite) dashboard, served by nginx
sdk/python/         client SDK
docker-compose.yml
.github/workflows/  CI/CD
```

## Possible extensions

* API keys per environment (dev / staging / prod)
* Server-sent events so SDKs receive flag changes instantly instead of polling
* Multivariate flags (A/B/C variants) instead of on/off
* Alembic migrations

## License

MIT
