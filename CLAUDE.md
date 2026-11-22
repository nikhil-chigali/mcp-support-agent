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

Early scaffolding. `packages/{store,mcp_server,agent}`, `docs/` and `evals/` are empty; `pyproject.toml`, `docker-compose.yml` and `justfile` are empty placeholders. Current work: Phase 0–1 (workspace, Postgres via docker compose, store models, Alembic migration 0001, seed).

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

## Database migrations (Alembic, SQLAlchemy 2.0)

- One Alembic setup per database: `packages/store/alembic/` and `packages/mcp_server/alembic/`, each with its own version table. Never share a migration history across them.
- Autogenerate is a first draft only. It misses `CHECK` constraints (add with `op.create_check_constraint`), the `lower(name)` expression index, and enum value changes. Review every generated file.
- The Store design SQL becomes migration 0001; after that, migrations are the schema's source of truth.
- Eval resets never touch the schema: `TRUNCATE ... RESTART IDENTITY CASCADE` + reseed.

## Commands

Planned in the design doc; the justfile is still empty, so adjust paths once code exists. `just` with no args lists recipes.

```
just up                # docker compose up -d (postgres + store + mcp server)
just migrate           # alembic upgrade head for store and mcp_server
just migration-check   # alembic check + downgrade base/upgrade head; destroys data — throwaway DB only
just seed              # uv run python -m store.seed
just test              # uv run pytest packages
just lint              # ruff check . && lint-imports
just serve-store       # uvicorn store.api:app --reload
just inspect           # MCP Inspector against the server over stdio
just agent             # uv run python -m agent.cli
just eval <args>       # uv run python -m evals.run
```

Single test: `uv run pytest packages/store/tests/test_policy.py::test_name`.

## Evals

- `evals/tickets/dev.jsonl` holds the 40 tuning tickets. **The 10 holdout tickets must stay out of the repo** (gitignored file or private gist) — never read or add them.
- Grading of outcome and amount is deterministic, from the case records; only reply text goes to an LLM judge.
- After any change to the agent prompt or tool descriptions: rerun the full set and commit the scores in `evals/results/` alongside the change.

## Open decisions

Record the outcome in the design doc when settled.
- Status columns: Postgres `ENUM` vs `TEXT` + `CHECK` (leaning `TEXT` + `CHECK`; must decide before migration 0001).
- R7 scope: per refund row, per item total, or per case (the DB check is per row; split refunds or multi-item cancels can slip past it).
- Case store: a second database in the same Postgres container (proposed) vs SQLite.
- How eval tickets reach the `tickets` table (seed vs harness), and seed dates relative to `FROZEN_NOW`.
- MCP SDK support for spec 2026-07-28 (`input_required`, `server/discover`); fall back to 2025-11-25 if needed.
