# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

An MCP server wrapping a fake kitchenware store's API (Hearth & Kettle), plus a Claude support agent that resolves refund tickets, scored by a 50-ticket eval suite.

This is a personal learning project for practising database → API → MCP → agent skills. Work proceeds one small, runnable step at a time. **The user decides per step whether they write the code or Claude does** — ask if it isn't clear, and when the user writes code, guide and review rather than taking over.

The design doc is the source of truth: **Support Desk MCP — Build Spec** (https://claude.ai/artifact/KHSMopoMYZ77Jn91qUa2vg). Read it with the Claude Docs tools, not web fetch. It has three tabs:
- *Build Spec* — goals, MCP tools/resources/prompts, agent loop, evals, phased build plan.
- *Store design* — business rules R1–R8, DB schema SQL, REST endpoints, error codes. Wins over Build Spec where they disagree.
- *Repo setup* — layout, boundary rule, justfile, Alembic conventions.

## Status

Phase 1 (store backend), database part. Done: uv workspace with all three packages (only `store` has code), Postgres via docker compose, store models (`store/models.py`), Alembic migration 0001, justfile. Next: seed script, then policy code and the REST API. `mcp_server`, `agent`, `docs/` and `evals/` are still empty.

## Local database

`just up` starts Postgres 18 on `localhost:5432`. The superuser comes from a gitignored `.env` (keys in `.env.example`) and is only used by the init script and `just psql`. `docker/postgres/init/01-databases.sql` runs once, on a fresh volume (`just reset-db` to re-run it), and creates:

| Database | Role (password = role name, dev only) | Use |
|---|---|---|
| `store` | `store_app` | store dev data |
| `store_test` | `store_app` | tests and `just migration-check` — may be wiped at any time |
| `cases` | `cases_app` | MCP server case store |
| `cases_test` | `cases_app` | its throwaway twin |

`CONNECT` is revoked from `PUBLIC`, so each role can open only its own databases — the boundary rule holds at the database level too. The store reads its URL from `STORE_DATABASE_URL` (pydantic-settings, `store/db.py`); the default is the dev `store` database. Alembic's `env.py` uses the same setting, so pointing `STORE_DATABASE_URL` at `store_test` retargets migrations too.

## Architecture

```
agent        Claude tool-use loop + host-side approval gate for destructive tools
  │ MCP only
mcp_server   tools · resources · prompts · its own case store (case_id state)
  │ HTTP only, via its own store_client.py written against the store's OpenAPI spec
store        FastAPI + Postgres; "the customer's system"; enforces refund policy in code
```

**Boundary rule (enforced, don't break it):** `mcp_server` never imports `store`; `agent` never imports `store` or `mcp_server`. Each package is its own uv workspace member with its own `pyproject.toml`, and import-linter contracts in the root `pyproject.toml` fail CI on violations. The case store is a separate database from the store's Postgres — the store never learns cases exist.

Where responsibilities live:
- **Money logic is the backend's.** The agent proposes an amount; the store recomputes eligibility and the maximum and rejects anything above it. `store/policy.py` holds R1–R8 and should have 100% test coverage.
- **R7 (refunds over $200 need a manager) and R8 (never refund past what was paid) are enforced twice**: in policy code and as DB `CHECK` constraints.
- **Manager approval comes from the server** via `input_required`, so it holds for any MCP host. The agent's yes/no gate on destructive tools is a second, host-side layer.
- **The model never supplies the fields that make a write safe.** The MCP server fills in the idempotency key (derived from case_id), `approved_by` (from the manager's answer) and `as_of` (the ticket's `created_at`, recorded at `open_case`).
- **Fault injection lives in the store** (`faults.py`: 429s, 500s, latency, renamed fields) so the server's error handling is exercised for real.

## Conventions

- Money is integer cents (`*_cents`), never floats.
- Dates are judged against when the ticket was filed (`as_of`), never "today". `FROZEN_NOW` pins the store clock for evals.
- Every write is idempotent (`Idempotency-Key` header; same key + different body → 409 `idempotency_conflict`) and audited against the case (`X-Case-Id` header → `audit_log.case_id`).
- Tickets have no `customer_id`/`order_id` on purpose — resolving who and which order is the agent's job.
- API errors use one envelope `{"error": {"code", "message", "details"}}`; codes map one-to-one to the MCP server's `isError` messages.
- Store API: base path `/v1`, `X-API-Key` on everything except `/health`.
- Status columns are Python `StrEnum`s stored as `VARCHAR(32)` + `CHECK` via `text_enum()` in `store/models.py` — never Postgres `ENUM`. Adding a value is a constraint swap in a migration.
- `Base.metadata` has a naming convention (`ck_<table>_<name>`, `fk_…`, `ix_…`); always give `CheckConstraint` a short `name=` so migrations can drop/replace it by name.
- DB-side defaults use `server_default`, so raw-SQL writers (seed, eval reset) get them too.

## Database migrations (Alembic, SQLAlchemy 2.0)

- One Alembic setup per database: `packages/store/alembic/` and `packages/mcp_server/alembic/`, each with its own version table. Never share a migration history across them.
- Run Alembic from `packages/store` (`cd packages/store && uv run alembic ...`). New revision: `uv run alembic revision --autogenerate --rev-id 0002 -m "..."`; ruff formats and lints it via post-write hooks.
- Autogenerate is a first draft only. For a new table it does include CHECK constraints and the `lower(name)` expression index; it does **not** detect a CHECK added to or changed on an existing table (write `op.drop_constraint` / `op.create_check_constraint` by hand). Review every generated file.
- Migration 0001 is the Store design SQL as models; migrations are now the schema's source of truth.
- `just migration-check` must pass before committing a migration.
- Eval resets never touch the schema: `TRUNCATE ... RESTART IDENTITY CASCADE` + reseed.

## Commands

`just` with no args lists recipes.

```
just up                # start Postgres and wait until healthy
just down              # stop it (data kept)
just reset-db          # wipe the volume, re-run the init script, migrate (asks first)
just psql [db]         # psql in the container; db defaults to store
just migrate           # alembic upgrade head on the dev store database
just migration-check   # on store_test only: base → head → alembic check → base → head
just lint              # ruff check + ruff format --check + lint-imports
just fmt               # ruff format + ruff check --fix
just test [args]       # uv run pytest packages [args]; exits 5 until tests exist
```

Single test: `just test packages/store/tests/test_policy.py::test_name`.

Planned recipes from the design doc, added when their code exists: `seed`, `serve-store`, `inspect` (MCP Inspector), `agent`, `eval`. `migrate` and `migration-check` gain `mcp_server` lines once the case store has its own Alembic setup.

## Evals

- `evals/tickets/dev.jsonl` holds the 40 tuning tickets. **The 10 holdout tickets must stay out of the repo** (gitignored file or private gist) — never read or add them.
- Grading of outcome and amount is deterministic, from the case records; only reply text goes to an LLM judge.
- After any change to the agent prompt or tool descriptions: rerun the full set and commit the scores in `evals/results/` alongside the change.

## Open decisions

Record the outcome in the design doc when settled.
- R7 scope: per refund row, per item total, or per case (the DB check is per row; split refunds or multi-item cancels can slip past it). Decide before writing `policy.py`.
- How eval tickets reach the `tickets` table (seed vs harness), and seed dates relative to `FROZEN_NOW`. Decide before writing the seed.
- MCP SDK support for spec 2026-07-28 (`input_required`, `server/discover`); fall back to 2025-11-25 if needed.

Settled (not yet written back to the design doc):
- Status columns: `VARCHAR` + `CHECK`, not Postgres `ENUM`.
- Case store: a second database (`cases`) in the same Postgres container, with its own role.
- Identity columns instead of `BIGSERIAL`; extra order-timestamp CHECKs; `refunds.rule` limited to R1–R5 by CHECK; indexes on lookup foreign keys.
