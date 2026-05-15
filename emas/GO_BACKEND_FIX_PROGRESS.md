# Go Backend Fix Progress Tracker

Date created: 2026-05-15

Purpose: track safe, incremental Go backend fixes from `GO_BACKEND_AUDIT.md`.

Status values:

- Not Started
- In Progress
- Blocked
- Done
- Deferred

## Current Baseline

| Item | Status | Notes |
|---|---|---|
| Audit documented | Done | See `GO_BACKEND_AUDIT.md`. |
| Existing service tests checked | Done | `go test ./internal/service -count=1` passed during audit and again on `audit/go-backend-phase-0` on 2026-05-15. |
| Existing e2e tests checked | Done | `go test ./internal/e2e -count=1` passed during audit and again on `audit/go-backend-phase-0` on 2026-05-15. |
| Full handler package checked | Blocked | `go test ./internal/handler -count=1 -timeout 180s -v` timed out. Bisection identified `TestAISchedulingHandler_Features` and `TestRealSolverProposalLifecycle` as proposal apply-by-ID timeout blockers on the shared SQLite test DB. |
| Swagger snapshot recorded | Done | Phase 0 snapshots saved under `docs/audit/phase0/swagger/`. |
| Docker Compose startup verified | Blocked | Non-invasive Compose checks only: worktree lacks `.env`, `emas/.env`, and `factory-agent/.env`; no Compose containers are running for this worktree. Startup was not attempted to avoid affecting other active chats/worktrees. |

## Phase 0: Safety Preparation

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Create backend fix branch | Done | Codex | Created `audit/go-backend-phase-0` from `audit/go-backend` at `afdb661`. |
| Run `go test ./internal/service -count=1` | Done | Codex | Passed on 2026-05-15. |
| Run `go test ./internal/e2e -count=1` | Done | Codex | Passed on 2026-05-15. |
| Bisect `internal/handler` timeout | Done | Codex | Full package timed out at `TestAISchedulingHandler_Features`; individual sweep also found `TestRealSolverProposalLifecycle` times out. All other individual handler tests passed with 60s timeouts. |
| Record key API response samples | Done | Codex | Samples saved under `docs/audit/phase0/api_responses/`; generated via `EMAS_CAPTURE_PHASE0_BASELINE=1 go test ./internal/audit -run TestCapturePhase0BaselineResponses -count=1 -v`. |
| Snapshot Swagger files | Done | Codex | Copied current `docs/swagger.json` and `docs/swagger.yaml` to `docs/audit/phase0/swagger/`. |
| Verify Docker Compose health | Blocked | Codex | Compose config requires missing worktree env files; startup not attempted to avoid affecting other active chats/worktrees. |

## Phase 1: Low-Risk Contract Cleanup

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Add Gin route vs Swagger parity test | Done | Codex | Added `internal/router/route_swagger_parity_test.go`; `go test ./internal/router -run TestRegisteredRoutesMatchSwagger -count=1 -v` passes after annotation cleanup. |
| Correct stale Swagger annotations for formulas | Done | Codex | Corrected `/formulas`, `/formulas/{id}`, and `/formulas/{id}/ingredients`. |
| Correct stale Swagger annotations for settings | Done | Codex | Corrected `GET/PUT /settings`. |
| Correct stale scheduling route annotations | Done | Codex | Corrected candidate machines, slot validation, earliest completion, training stats/backfill, and refresh calendars. |
| Correct stale reports route annotations | Done | Codex | Corrected `/reports/oee` and `/reports/bottlenecks`; removed unregistered helper annotation. |
| Correct production log annotation | Done | Codex | Corrected `POST /production-logs`. |
| Correct chatbot approval annotations | Done | Codex | Corrected `/ai/chatbot/approvals/...` and `/ai/chats/{id}/approvals`. |
| Regenerate Swagger | Done | Codex | Regenerated `docs/docs.go`, `docs/swagger.json`, and `docs/swagger.yaml`, then ran `scripts/enrich_swagger_id_patterns.py`. |
| Run tools.md generation smoke test | Done | Codex | Non-mutating Factory Agent smoke parsed regenerated Swagger into 138 tools and rendered tools.md in memory; corrected Phase 1 endpoints were present. |

## Phase 2: API and Contract Fixes

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Decide public JSON field naming rule | Done | Codex | Documented in `GO_BACKEND_ENGINEERING_RULES.md`: new public response DTO fields use `snake_case`; legacy raw domain casing stays only with golden contract coverage until intentional migration. |
| Add golden response tests for jobs | Done | Codex | Added `TestAPIContractGoldenJobs`; locks job response shape including `deadline_status`. |
| Add golden response tests for machines | Done | Codex | Added `TestAPIContractGoldenMachines`; captures current legacy raw-domain casing such as `MachineID`. |
| Add golden response tests for products/formulas | Done | Codex | Added `TestAPIContractGoldenProductsAndFormulas`; captures current product/formula response casing. |
| Add golden response tests for inventory | Done | Codex | Added `TestAPIContractGoldenInventory`; covers materials, product stock, and reservations. |
| Standardize error envelope | Done | Codex | Idempotency and auth middleware errors now return `dto.Response{success:false,error:...}`; covered by middleware envelope test. |
| Map validation errors to 400/422 consistently | Done | Codex | Kept binding/syntax errors as 400; mapped semantic invalid time windows for machine downtime and maintenance to 422 with handler tests. Broader service error taxonomy remains Phase 4 scope. |

## Phase 3: Backend Test Improvement

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Add inventory insufficient-stock tests | Not Started | TBD | Consume should not silently oversubtract unless explicitly allowed. |
| Add inventory transaction rollback tests | Not Started | TBD | Stock update and transaction insert must be atomic. |
| Add job create rollback tests | Not Started | TBD | Job, steps, slots should commit or rollback together. |
| Add production log rollback tests | Not Started | TBD | Log, slot, step, job, inventory updates should be atomic. |
| Add auth protected-route tests | Not Started | TBD | Missing headers should not default to planner in secure mode. |
| Add idempotency concurrency tests | Not Started | TBD | Same key and payload should replay once. |
| Add scheduling overlap/calendar regression tests | Not Started | TBD | Include maintenance and downtime constraints. |

## Phase 4: Backend Architecture Refactoring

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Add transaction wrapper for job create | Not Started | TBD | Keep API response stable. |
| Add transaction wrapper for job delete | Not Started | TBD | Do not ignore child delete errors. |
| Add transaction wrapper for production logs | Not Started | TBD | Avoid partial execution updates. |
| Add transaction-safe inventory consume/receive | Not Started | TBD | Consider row locks under MySQL. |
| Introduce backend error mapper | Not Started | TBD | Small taxonomy: validation, not found, conflict, forbidden, internal. |
| Extract public response DTO mapping | Deferred | TBD | Do after golden response tests. |
| Split oversized AI scheduling service | Deferred | TBD | Only after contract and regression tests. |

## Phase 5: Long-Term Improvements

| Task | Status | Owner | Evidence / Notes |
|---|---|---|---|
| Move production schema changes to versioned migrations | Not Started | TBD | Keep `AutoMigrate` for tests/local until migration flow exists. |
| Add structured request logging/correlation IDs | Not Started | TBD | Build on existing request context/logger. |
| Add performance smoke tests for scheduling APIs | Not Started | TBD | Focus batch proposal and reschedule-all. |
| Add deployment rollback notes | Not Started | TBD | Include DB migration rollback. |
| Add API contract release checklist | Not Started | TBD | Include Swagger and tools.md regeneration. |

## Decision Log

| Date | Decision | Reason | Follow-Up |
|---|---|---|---|
| 2026-05-15 | Fix OpenAPI drift before runtime refactors | Factory Agent depends on accurate generated tools. | Add route parity test first. |
| 2026-05-15 | Do not refactor scheduler internals first | Proposal apply has specialized logic and existing tests. | Add regression/contract protection before touching. |
| 2026-05-15 | Prefer incremental transactions over big rewrite | Reduces partial-write risk without changing API behavior. | Start with job and production-log paths. |
| 2026-05-15 | Use snake_case for new public response DTO fields while preserving tested legacy raw-domain responses | Prevents silent casing drift without forcing a broad breaking response migration in Phase 2. | Migrate raw domain responses behind explicit DTO mapping in a later phase. |

## Next Recommended Action

Begin Phase 3 backend test improvement: add inventory insufficient-stock/rollback tests, job and production-log rollback tests, auth protected-route tests, idempotency concurrency tests, and scheduling regression coverage.

