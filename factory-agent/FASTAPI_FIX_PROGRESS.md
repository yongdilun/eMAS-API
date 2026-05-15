# Factory Agent FastAPI Fix Progress

Purpose: Track cleanup progress for the FastAPI backend without losing rollback safety.

Status key:

- Not Started
- In Progress
- Blocked
- Done
- Deferred

## Baseline

| Item | Status | Owner | Notes |
|---|---|---|---|
| Create cleanup branch | Done | Codex | Created `codex/phase-0-fastapi-safety` from current `origin/main` on 2026-05-15 after deleting merged temporary branch `recover-execution-refactor`. |
| Run `pytest --collect-only -q` | Done | Codex | 487 tests collected on 2026-05-15. |
| Run full test suite | Done | Codex | `pytest`: 464 passed, 3 skipped, 20 xfailed on 2026-05-15. |
| Capture OpenAPI snapshot | Done | Codex | Saved `docs/baselines/openapi.phase0.json` with 33 paths and 26 component schemas. |
| Capture Docker build/import baseline | Done | Codex | `docker build -t factory-agent-phase0-baseline .` passed; container `import main` smoke passed. |
| Record current frontend/API behavior | Done | Codex | Recorded in `docs/baselines/phase0_behavior.md`; no runtime behavior changes made. |

## Issue Tracker

| ID | Issue | Severity | Phase | Status | Verification | Rollback |
|---|---|---|---|---|---|---|
| FA-001 | Protect unauthenticated SSE, DLQ, and metrics reads | High | 2 | Done | Auth contract tests for SSE, DLQ, and metrics passed; full `pytest` passed | Temporary local-only compatibility flag |
| FA-002 | Fail unsafe production auth/admin defaults | High | 2 | Done | Production config tests passed; full `pytest` passed | Strict-mode flag rollback |
| FA-003 | Make plan persistence atomic | High | 2 | Done | Injected failure rollback test and approval resume regression passed; full `pytest` passed | Restore old helper behind flag |
| FA-004 | Move startup schema mutation to migrations | High | 5 | Not Started | Migration smoke tests | Keep startup compat under explicit flag |
| FA-005 | Split mixed-responsibility API router | High | 4 | In Progress | OpenAPI diff plus endpoint tests | Revert one extracted router/module |
| FA-006 | Reduce SSE database polling risk | Medium | 5 | Not Started | Disconnect and concurrent stream tests | Keep old implementation path |
| FA-007 | Strengthen relational constraints/session cleanup | Medium | 4 | Done | Session deletion contract covers session-owned rows; full `pytest -q` passed | Revert session cleanup service extraction |
| FA-008 | Document legacy vs graph-native API contracts | Medium | 3 | Done | `tests/test_phase3_contract_coverage.py`; full `pytest -q` passed | Keep retired endpoints returning 410 |
| FA-009 | Align dependency and Docker packaging | Medium | 1 | Done | `docker build -t factory-agent-phase1-cleanup .`; container `import main` smoke passed | Revert ignore/dependency edits |
| FA-010 | Replace mutable JSON defaults | Low/Medium | 1 | Done | `tests/test_model_json_defaults.py`; full `pytest` passed with project-local temp dir | Revert model default change |
| FA-011 | Add missing auth/contract coverage | Medium | 3 | Done | `tests/test_phase3_contract_coverage.py`; related auth/rollback tests; full `pytest -q` passed | Revert tests independently |

## Phase Progress

### Phase 0: Safety Preparation

- Status: Done
- Goal: Freeze current behavior and make rollback easy.
- Next actions:
  - Completed on `codex/phase-0-fastapi-safety`.
  - Use this baseline before starting Phase 1 cleanup.

### Phase 1: Low-Risk Cleanup

- Status: Done
- Goal: Reduce repository and deployment noise without changing behavior.
- Completed:
  - Created `codex/phase-1-fastapi-cleanup` from `codex/phase-0-fastapi-safety`.
  - Expanded `.dockerignore` for local databases, logs, caches, scratch folders, vector DBs, and pickle artifacts.
  - Identified tracked local artifacts (`factory_agent.db`, scratch scripts, `factory_agent/rag/bm25_index.pkl`) as Docker packaging exclusions; the RAG retriever handles a missing BM25 pickle by falling back without keyword results.
  - Aligned package metadata to use `requirements.txt` as the single runtime dependency source via dynamic setuptools dependencies.
  - Replaced mutable JSON ORM defaults with callable defaults and added isolation tests.
- Deferred:
  - Moving pure helper functions from `routes.py`; route/helper extraction is safer after Phase 3 contract coverage and belongs with Phase 4 router refactoring.
- Verification:
  - `pytest tests/test_model_json_defaults.py -q`: 2 passed.
  - `pytest tests/test_model_json_defaults.py tests/test_mysql_schema.py tests/test_schema_compatibility.py -q`: 3 passed, 1 skipped.
  - `pytest`: 466 passed, 3 skipped, 20 xfailed after setting `TMP`/`TEMP` to a project-local temp directory; default Windows temp root was inaccessible.
  - `docker build -t factory-agent-phase1-cleanup .`: passed.
  - `docker run --rm factory-agent-phase1-cleanup python -c "import main; print('import main ok')"`: passed.

### Phase 2: Bug Fixes and Contract Fixes

- Status: Done
- Goal: Fix security and data-integrity risks.
- Completed:
  - Added JWT enforcement to session event streams and DLQ reads.
  - Protected metrics behind the admin API key policy.
  - Added production startup validation for JWT/admin defaults, with an explicit unsafe override for rollback.
  - Made plan row, step row, session pointer, and plan message persistence commit atomically.
  - Preserved approved graph resume snapshots so completed writes expose their tool result before completion is accepted by tests.
- Verification:
  - `pytest tests/test_config_app_mode.py tests/test_api_endpoints.py::test_stream_dlq_and_metrics_reads_require_auth tests/test_api_endpoints.py::test_metrics_endpoint_exposes_prometheus_format tests/test_api_endpoints.py::test_admin_dashboard_requires_x_admin_key tests/test_api_endpoints.py::test_create_plan_rolls_back_when_plan_message_persistence_fails tests/test_api_endpoints.py::test_create_plan_persists_plan_and_steps tests/test_tool_output_alignment.py tests/test_reliability_e2e.py::test_pause_resume_live_instruction_update_rejects_stale_approval_and_completes -q`: 19 passed.
  - `pytest tests/test_config_app_mode.py tests/test_approval_atomicity.py -q`: 15 passed.
  - `pytest tests/test_reliability_e2e.py -q`: 3 passed.
  - `pytest tests/test_api_endpoints.py -q`: 46 passed, 20 xfailed.
  - `pytest -q`: 472 passed, 4 skipped, 20 xfailed after setting `TMP`/`TEMP` to a project-local temp directory.
- Remaining:
  - None for Phase 2.

### Phase 3: Test Coverage Improvement

- Status: Done
- Goal: Add tests that make refactoring safe.
- Completed:
  - Added `docs/contracts/legacy_graph_native_contracts.md` documenting active graph-native contracts, deprecated SSE compatibility streams, and retired legacy approval/DLQ write contracts.
  - Added `tests/test_phase3_contract_coverage.py` with an OpenAPI path/response snapshot for route-refactor safety.
  - Added OpenAPI auth documentation checks for sensitive JWT-protected user endpoints and admin-key-protected operational endpoints.
  - Added legacy/graph-native compatibility matrix tests covering retired `plan` and `step` approval decisions returning `410`, retired DLQ write/replay endpoints returning `410`, and active graph-native approval reads.
  - Reused existing Phase 2 coverage for SSE/DLQ/metrics auth and plan persistence rollback because those gaps are already closed and passing.
- Verification:
  - `pytest tests/test_phase3_contract_coverage.py -q`: 10 passed.
  - `pytest tests/test_phase3_contract_coverage.py tests/test_api_endpoints.py::test_stream_dlq_and_metrics_reads_require_auth tests/test_api_endpoints.py::test_metrics_endpoint_exposes_prometheus_format tests/test_api_endpoints.py::test_create_plan_rolls_back_when_plan_message_persistence_fails tests/test_api_endpoints.py::test_create_plan_persists_plan_and_steps tests/test_planner_service_phase6.py::test_graph_native_snapshot_uses_checkpoint_projection_not_legacy_steps tests/test_planner_service_phase6.py::test_legacy_step_reject_cannot_mutate_graph_native_session tests/test_phase8_legacy_retirement.py -q`: 18 passed.
  - `pytest -q`: 482 passed, 4 skipped, 20 xfailed after setting `TMP`/`TEMP` to a project-local temp directory.
- Remaining:
  - None for Phase 3.

### Phase 4: Architecture Refactoring

- Status: In Progress
- Goal: Improve locality by separating route, service, and projection responsibilities.
- Started:
  - Began FA-005 on 2026-05-15 with a small router/service extraction slice guarded by Phase 3 OpenAPI and compatibility tests.
  - Began FA-007 on 2026-05-15 by centralizing session-owned row cleanup behind a service and expanding session deletion contract coverage.
- Completed:
  - Centralized JWT and admin dependency factories in `factory_agent/api/dependencies.py`.
  - Split session lifecycle routes (`POST/GET/PATCH/DELETE /sessions`) into `factory_agent/api/routers/sessions.py`.
  - Moved session response mapping into `factory_agent/api/response_mappers.py` so extracted routers do not import the mixed route module.
  - Moved session deletion cleanup into `factory_agent/services/session_cleanup.py`.
  - Expanded the session deletion contract test to cover messages, plans, steps, approvals, dead letters, execution snapshots, workflow checkpoints, and session-scoped vector memories.
- Verification:
  - Baseline before route code changes: `pytest tests/test_phase3_contract_coverage.py -q`: 10 passed.
  - `pytest tests/test_api_endpoints.py::test_create_session_and_message_updates_intent tests/test_api_endpoints.py::test_delete_session_removes_session_and_related_rows tests/test_api_endpoints.py::test_admin_dashboard_requires_x_admin_key tests/test_api_endpoints.py::test_stream_dlq_and_metrics_reads_require_auth tests/test_phase3_contract_coverage.py -q`: 14 passed.
  - `pytest tests/test_api_endpoints.py tests/test_approval_atomicity.py tests/test_session_manager.py -q`: 57 passed, 20 xfailed.
  - `pytest tests/test_planner_service_phase6.py::test_graph_native_snapshot_uses_checkpoint_projection_not_legacy_steps tests/test_planner_service_phase6.py::test_legacy_step_reject_cannot_mutate_graph_native_session tests/test_reliability_e2e.py::test_pause_resume_live_instruction_update_rejects_stale_approval_and_completes -q`: 3 passed.
  - Required contract guard after changes: `pytest tests/test_phase3_contract_coverage.py -q`: 10 passed.
  - Full suite: `pytest -q`: 482 passed, 4 skipped, 20 xfailed.
- Remaining:
  - FA-005 remains In Progress. Only the sessions route slice was split; messages, plans, approvals, events, snapshots, admin, and DLQ remain in the mixed router.
  - Snapshot/timeline projection, approval resume task handling, and plan persistence were not moved in this slice because they are tightly coupled to graph/checkpoint behavior and should be extracted one at a time with the same contract guard.
- Deferred:
  - DB-level foreign key/cascade changes are deferred to migration-backed work so Phase 4 does not introduce implicit schema mutation outside the Phase 5 migration plan.
- Candidate changes:
  - Split routers by domain.
  - Move snapshot/timeline projection to a service.
  - Move approval resume task handling to a service.
  - Move plan persistence to a transaction-focused service.
  - Centralize auth/admin dependencies.

### Phase 5: Long-Term Improvements

- Status: Not Started
- Goal: Improve deployment, observability, and runtime scalability.
- Candidate changes:
  - Replace startup schema mutation with migrations.
  - Add readiness checks.
  - Optimize event delivery.
  - Profile graph compilation and checkpointing.

## Decision Log

| Date | Decision | Reason | Follow-up |
|---|---|---|---|
| 2026-05-15 | Scope cleanup to `factory-agent` FastAPI backend | User requested FastAPI-only cleanup | Avoid touching frontend or Go API unless needed for contracts |
| 2026-05-15 | Do not start with a rewrite | Current behavior has broad tests and migration history | Prefer phased, rollback-safe changes |
| 2026-05-15 | Fix security/data integrity before router splitting | These reduce risk fastest | Add tests first |

## Current Next Step

Phase 4 is in progress after a completed safe extraction slice:

1. Continue FA-005 by extracting the next safest domain router while preserving the Phase 3 OpenAPI contract snapshot.
2. Prefer messages or DLQ/admin reads before snapshot, approval resume, or plan persistence extraction.
3. Keep DB-level cascade constraints deferred until explicit migration work.
