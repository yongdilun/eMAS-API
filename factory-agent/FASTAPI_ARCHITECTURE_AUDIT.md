# Factory Agent FastAPI Architecture Audit

Date: 2026-05-15

Scope: `factory-agent` FastAPI backend only. This audit is intentionally read-only and does not require a rewrite. The goal is safe cleanup that preserves current working behavior.

## 1. Executive Summary

The FastAPI agent has a strong amount of behavior coverage and a clear migration direction toward LangGraph-native planning, graph approvals, checkpointing, and safe write bundles. The strongest areas are Pydantic API schemas, plan validation, tool registry tests, permission tests, and graph/write-safety tests.

The biggest risks are:

- Several read/stream endpoints appear unauthenticated.
- Runtime schema compatibility DDL runs during app startup.
- `factory_agent/api/routes.py` has grown into a large mixed-responsibility module.
- Plan persistence uses multiple commits, which can leave partial state if a later write fails.
- Legacy compatibility behavior and graph-native behavior are interleaved in the same route layer.

Overall recommendation: fix security and data-integrity risks first, then add contract tests, then split route responsibilities in small steps.

## 2. Current Architecture Map

### Main Entry Point

- `main.py` creates the FastAPI app, lifespan, CORS, `/health`, optional wiki static mount, database tables, tool registry, Redis event bus, worker queues, and the API router.
- `factory_agent/api/routes.py` builds the API router and contains most route handlers plus many internal helpers.

### Main Subsystems

- `factory_agent/api`: route definitions, response projection, SSE streams, admin endpoints, approval endpoints, plan/session/message endpoints.
- `factory_agent/schemas.py`: Pydantic request and response contracts.
- `factory_agent/persistence`: SQLAlchemy database/session setup and ORM models.
- `factory_agent/services/planner_service.py`: LangGraph planner facade, retries, deduplication, and argument provenance cleanup.
- `factory_agent/graph`: LangGraph graph construction, checkpointing, planner graph, graph nodes, approval and write flow.
- `factory_agent/planning`: tool selection, intent handling, tool scope, plan validation, reasoning pipeline.
- `factory_agent/security`: JWT validation, role permissions, and tool argument guardrails.
- `factory_agent/observability`: structured logging, metrics, and event bus.
- `factory_agent/rag`: ingestion, retrieval, reranking, answer generation.

### Runtime Flow

1. App startup loads settings, creates tables, applies schema compatibility DDL, initializes tool registry and event bus.
2. Requests enter the router produced by `build_router`.
3. Session and message endpoints persist user state.
4. Plan creation invokes `PlannerService`.
5. `PlannerService` invokes the LangGraph planner.
6. Graph nodes select tools, run reads, stage writes, validate plans, request approval, or commit.
7. State is stored in SQL tables and graph workflow checkpoints.
8. Snapshot and SSE endpoints project database/checkpoint state back to clients.

### Risky Boundaries

- The route layer contains persistence, orchestration, projection, auth dependency definitions, SSE behavior, RAG fallback, approval resume tasks, and admin behavior.
- `factory_agent/api/dependencies.py` exists but route dependencies are defined inside `routes.py`.
- Legacy relational plan-step compatibility and graph-native execution are both handled inside the same API module.

## 3. Problems Found

### Problem 1: Unauthenticated Event, DLQ, and Metrics Reads

- Severity: High
- Risk Type: Security / Contract
- Affected Area:
  - `factory_agent/api/routes.py`
  - `/sessions/{session_id}/events/semantic`
  - `/sessions/{session_id}/events/activity`
  - `/sessions/{session_id}/events`
  - `GET /dlq`
  - `GET /metrics`
- Evidence: These handlers use database dependencies but do not consistently require `require_jwt` or `require_admin`.
- Why This Is a Problem: Streams and DLQ entries can reveal session state, approval IDs, error details, and operational behavior.
- Possible Impact: Data leakage, visibility into approval workflows, scraping of operational state.
- Recommended Fix: Add auth to stream and DLQ read endpoints. Decide whether `/metrics` is admin-only, local-only, or protected by infrastructure.
- Safe Implementation Notes: If browser `EventSource` cannot send Authorization headers, use a short-lived signed stream token or secure cookie-based auth.
- Tests Needed: Unauthorized requests return `401` or `403`; authorized requests still work.
- Rollback Plan: Temporary local-dev flag such as `ALLOW_UNAUTH_LOCAL_STREAMS=1`, disabled in production.

### Problem 2: Unsafe Auth and Admin Defaults

- Severity: High
- Risk Type: Security / Config
- Affected Area:
  - `factory_agent/config.py`
- Evidence: `jwt_required` defaults to false and `admin_api_key` defaults to `changeme-admin-key`.
- Why This Is a Problem: Missing production env vars can silently create a permissive deployment.
- Possible Impact: Known admin key, unauthenticated access paths, unsafe production startup.
- Recommended Fix: In production mode, fail startup if JWT is disabled, `JWT_SECRET` is missing, or admin key remains the default.
- Safe Implementation Notes: Preserve development defaults, but make production fail fast.
- Tests Needed: Config tests for production failure and development compatibility.
- Rollback Plan: Introduce strict behavior behind `STRICT_PRODUCTION_CONFIG=1`, then make it default after validation.

### Problem 3: API Router Is a Mixed-Responsibility Module

- Severity: High
- Risk Type: Architecture / Maintainability
- Affected Area:
  - `factory_agent/api/routes.py`
- Evidence: The router file is approximately 3,669 lines and contains route handlers, projection helpers, RAG fallback, planner orchestration, approval resume tasks, SSE streams, DB writes, and admin HTML.
- Why This Is a Problem: Small behavior changes require understanding many unrelated flows.
- Possible Impact: Higher regression risk, slow reviews, unclear ownership.
- Recommended Fix: Split into route modules for sessions, messages, plans, approvals, events, snapshots, and admin. Move shared orchestration into service modules.
- Safe Implementation Notes: Preserve public route paths and response models exactly.
- Tests Needed: OpenAPI snapshot and targeted endpoint tests before and after each extraction.
- Rollback Plan: Extract one module per PR so any move can be reverted independently.

### Problem 4: Runtime Schema Migration During Startup

- Severity: High
- Risk Type: Deployment / Database
- Affected Area:
  - `main.py`
- Evidence: Startup runs `Base.metadata.create_all` and `_ensure_schema_compatibility`, including `ALTER TABLE` statements.
- Why This Is a Problem: App startup can mutate production schema, lock tables, partially apply DDL, or hide migration drift.
- Possible Impact: Failed deploys, inconsistent schemas, hard rollback.
- Recommended Fix: Move DDL into explicit migrations. Keep startup checks read-only.
- Safe Implementation Notes: Convert current compatibility logic into migration scripts first.
- Tests Needed: SQLite/MySQL migration smoke tests.
- Rollback Plan: Keep compatibility mutation behind `ENABLE_STARTUP_SCHEMA_COMPAT=1` during transition.

### Problem 5: Plan Persistence Uses Multiple Commits

- Severity: High
- Risk Type: Bug / Data Integrity
- Affected Area:
  - `factory_agent/api/routes.py`
  - `_persist_plan`
- Evidence: Plan insert, step insert, session update, and message insert are committed in separate stages.
- Why This Is a Problem: A later failure can leave partial plan/session/message state.
- Possible Impact: Broken snapshots, orphaned plans, confusing timeline output.
- Recommended Fix: Use one explicit transaction for plan, steps, session update, and assistant plan message. Publish events after commit.
- Safe Implementation Notes: Use `flush()` to get IDs instead of intermediate commits.
- Tests Needed: Inject failure after plan creation and verify rollback leaves no partial rows.
- Rollback Plan: Keep old helper available until transactional helper passes regression tests.

### Problem 6: Long-Lived SSE Streams Poll the Database Per Connection

- Severity: Medium
- Risk Type: Performance / Reliability
- Affected Area:
  - `factory_agent/api/routes.py`
  - SSE endpoints
- Evidence: Generators loop forever and call snapshot loading every 0.5 to 1.0 seconds.
- Why This Is a Problem: Many clients multiply database load and keep DB sessions open for a long time.
- Possible Impact: Pool pressure, slow snapshots, noisy operational metrics.
- Recommended Fix: Prefer event/cursor notification stream. Use short database sessions per poll and detect disconnects.
- Safe Implementation Notes: Keep old semantic/activity streams deprecated but stable.
- Tests Needed: Disconnect tests, heartbeat tests, concurrent stream load test.
- Rollback Plan: Preserve current endpoint paths while switching implementation internally.

### Problem 7: Weak Relational Constraints and Manual Cascades

- Severity: Medium
- Risk Type: Data Integrity / Maintainability
- Affected Area:
  - `factory_agent/persistence/models.py`
  - session deletion route
- Evidence: Session deletion manually deletes related rows. Some `session_id` columns are not declared as foreign keys.
- Why This Is a Problem: Any missed table creates orphaned data.
- Possible Impact: Incorrect snapshots, storage growth, broken admin reports.
- Recommended Fix: Add foreign keys and cascade rules where supported. Centralize session deletion in a repository/service.
- Safe Implementation Notes: First add tests that enumerate all session-owned tables.
- Tests Needed: Deletion contract tests covering all session-owned models.
- Rollback Plan: Keep manual deletion as a fallback during migration.

### Problem 8: Legacy and Graph-Native Contracts Are Entangled

- Severity: Medium
- Risk Type: Architecture / Contract
- Affected Area:
  - `factory_agent/api/routes.py`
  - `tests/test_api_endpoints.py`
- Evidence: Retired legacy routes return `410`, while many tests still carry `legacy_compatibility` markers.
- Why This Is a Problem: Migration rules are spread across handlers and tests.
- Possible Impact: Accidental behavior changes when removing compatibility code.
- Recommended Fix: Create an explicit compatibility matrix: active, deprecated, retired, removed.
- Safe Implementation Notes: Do not remove legacy rows or endpoints until consumers are verified.
- Tests Needed: Contract tests for each retired endpoint and graph-native replacement.
- Rollback Plan: Keep retired endpoints returning `410` until migration is complete.

### Problem 9: Deployment Artifact Drift

- Severity: Medium
- Risk Type: Deployment / Maintainability
- Affected Area:
  - `pyproject.toml`
  - `requirements.txt`
  - `Dockerfile`
  - `.dockerignore`
- Evidence: `pyproject.toml` and `requirements.txt` do not describe the same dependency set. Docker copies the whole app and `.dockerignore` does not exclude database, pickle, logs, scratch, or vector DB artifacts.
- Why This Is a Problem: Local package install and container runtime can diverge.
- Possible Impact: Build drift, oversized images, accidental artifact shipping.
- Recommended Fix: Pick one runtime dependency source. Extend `.dockerignore`.
- Safe Implementation Notes: Confirm whether packaged indexes are intentional before ignoring them.
- Tests Needed: Docker build and import smoke test.
- Rollback Plan: Revert ignore changes if a required runtime artifact is excluded.

### Problem 10: Mutable JSON Defaults in ORM Models

- Severity: Low / Medium
- Risk Type: Bug / Data Integrity
- Affected Area:
  - `factory_agent/persistence/models.py`
- Evidence: Several JSON columns use `default={}` or `default=[]`.
- Why This Is a Problem: Mutable defaults are easy to misuse and can produce surprising behavior.
- Possible Impact: Shared or incorrect default JSON values in future changes.
- Recommended Fix: Use callable defaults such as `default=dict` and `default=list`.
- Safe Implementation Notes: Low-risk model cleanup if DB server defaults are not changed.
- Tests Needed: Create two rows, mutate one JSON value, verify isolation.
- Rollback Plan: Revert model default change only.

### Problem 11: Missing Contract Guards Around Exposed Endpoints

- Severity: Medium
- Risk Type: Testing
- Affected Area:
  - `tests`
- Evidence: 487 tests are collected, but auth coverage is stronger for approvals/JWT than for SSE, DLQ reads, and metrics.
- Why This Is a Problem: Security and stream contract changes can regress silently.
- Possible Impact: Broken frontend streaming or accidental endpoint exposure.
- Recommended Fix: Add focused contract tests before route refactoring.
- Safe Implementation Notes: Use existing in-memory DB fixtures.
- Tests Needed: SSE auth, DLQ auth, metrics policy, transactional rollback tests.
- Rollback Plan: Tests can be reverted independently.

## 4. Phased Fix Plan

### Phase 0: Safety Preparation

- Goal: Freeze current behavior before cleanup.
- What to change: Create branch, run tests, capture OpenAPI schema, capture Docker/import baseline, document critical flows.
- What not to change: Runtime behavior.
- Risk level: Low.
- Expected benefit: Safe rollback and measurable contracts.
- Verification steps:
  - `pytest --collect-only -q`
  - full `pytest`
  - OpenAPI snapshot
  - Docker build/import smoke

### Phase 1: Low-Risk Cleanup

- Goal: Reduce noise and accidental deploy risk.
- What to change: Expand `.dockerignore`, identify runtime artifacts, move pure helper functions from `routes.py`, replace mutable JSON defaults.
- What not to change: Endpoints, response schemas, planner behavior.
- Risk level: Low.
- Expected benefit: Cleaner repo and safer packaging.
- Verification steps:
  - Targeted model tests
  - Full tests
  - Docker build/import smoke

### Phase 2: Bug Fixes and Contract Fixes

- Goal: Close security and data integrity issues.
- What to change: Protect stream/DLQ/metrics endpoints, enforce production config, make plan persistence transactional.
- What not to change: Route paths or response bodies unless intentional and documented.
- Risk level: Medium.
- Expected benefit: Fastest risk reduction.
- Verification steps:
  - Auth tests
  - Approval flow tests
  - Snapshot tests
  - Transaction rollback tests

### Phase 3: Test Coverage Improvement

- Goal: Make refactoring safer.
- What to change: Add API contract snapshots, SSE disconnect tests, schema migration checks, Docker/import tests.
- What not to change: Production behavior except small testability seams.
- Risk level: Low.
- Expected benefit: Refactors become predictable.
- Verification steps:
  - CI passes
  - No new skipped core tests

### Phase 4: Architecture Refactoring

- Goal: Separate route, orchestration, persistence, and projection responsibilities.
- What to change: Split routers; move snapshot/timeline projection to services; move approval resume and plan persistence to services; centralize dependencies.
- What not to change: Public API paths.
- Risk level: Medium.
- Expected benefit: Better locality and lower regression risk.
- Verification steps:
  - OpenAPI snapshot diff
  - Endpoint contract tests
  - Approval and graph regression tests

### Phase 5: Long-Term Improvements

- Goal: Improve deployment and runtime resilience.
- What to change: Replace startup DDL with migrations, improve readiness checks, optimize stream delivery, profile planner graph compilation and checkpointing.
- What not to change: Planner semantics without regression corpus evidence.
- Risk level: Medium.
- Expected benefit: More reliable production behavior.
- Verification steps:
  - Migration smoke
  - Load/backpressure tests
  - Graph approval resume tests

## 5. Priority Table

| Priority | Issue | Severity | Risk | Recommended Phase | Expected Benefit |
|---|---|---|---|---|---|
| P0 | Unauthenticated streams, DLQ, metrics | High | Security | Phase 2 | Prevent data exposure |
| P0 | Unsafe production auth/admin defaults | High | Security | Phase 2 | Prevent unsafe deploys |
| P1 | Partial plan persistence | High | Bug | Phase 2 | Prevent corrupt session state |
| P1 | Startup schema mutation | High | Deployment | Phase 5 | Safer deploys |
| P1 | Mixed-responsibility router | High | Architecture | Phase 4 | Lower regression risk |
| P2 | SSE database polling per connection | Medium | Performance | Phase 5 | Better scalability |
| P2 | Weak FK/manual cascade cleanup | Medium | Data integrity | Phase 4 | Fewer orphan rows |
| P2 | Legacy/graph contract entanglement | Medium | Maintainability | Phase 3/4 | Clear migration path |
| P3 | Dependency/Docker drift | Medium | Deployment | Phase 1 | Reproducible builds |
| P3 | Mutable JSON defaults | Low/Medium | Bug | Phase 1 | Safer ORM defaults |

## 6. Safe Execution Checklist

- Create a branch.
- Run existing tests.
- Record current behavior.
- Capture OpenAPI/schema snapshot.
- Capture Docker/build baseline.
- Apply the smallest possible change.
- Run targeted tests.
- Run full tests.
- Check API/frontend behavior.
- Check logs and metrics.
- Commit with a clear message.
- Keep rollback possible.

## 7. Final Recommendation

Fix first:

- Unauthenticated streams, DLQ reads, and metrics policy.
- Unsafe production auth/admin defaults.
- Transactional plan persistence.

Delay:

- Large router splitting until contract tests are stronger.
- Legacy removal until active/deprecated/retired behavior is documented.

Risky to touch now:

- LangGraph planner semantics.
- Approval resume and checkpoint behavior.
- Compatibility plan projection logic.

Highest-value architecture improvement:

- Split `routes.py` by responsibility after OpenAPI and endpoint contract snapshots are in place.

Fastest bug reduction:

- Add endpoint auth tests, secure exposed endpoints, and make plan persistence atomic.
