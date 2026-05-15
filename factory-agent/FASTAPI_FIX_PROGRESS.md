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
| Create cleanup branch | Not Started | TBD | Use a dedicated branch before code changes. |
| Run `pytest --collect-only -q` | Done | Codex | 487 tests collected on 2026-05-15. |
| Run full test suite | Not Started | TBD | Needed before behavior changes. |
| Capture OpenAPI snapshot | Not Started | TBD | Save as contract baseline before route refactors. |
| Capture Docker build/import baseline | Not Started | TBD | Needed before `.dockerignore` and dependency cleanup. |
| Record current frontend/API behavior | Not Started | TBD | Especially snapshot, SSE, approvals, and plan creation. |

## Issue Tracker

| ID | Issue | Severity | Phase | Status | Verification | Rollback |
|---|---|---|---|---|---|---|
| FA-001 | Protect unauthenticated SSE, DLQ, and metrics reads | High | 2 | Not Started | Auth contract tests for each endpoint | Temporary local-only compatibility flag |
| FA-002 | Fail unsafe production auth/admin defaults | High | 2 | Not Started | Production config tests | Strict-mode flag rollback |
| FA-003 | Make plan persistence atomic | High | 2 | Not Started | Injected failure rollback tests | Restore old helper behind flag |
| FA-004 | Move startup schema mutation to migrations | High | 5 | Not Started | Migration smoke tests | Keep startup compat under explicit flag |
| FA-005 | Split mixed-responsibility API router | High | 4 | Not Started | OpenAPI diff plus endpoint tests | Revert one extracted router/module |
| FA-006 | Reduce SSE database polling risk | Medium | 5 | Not Started | Disconnect and concurrent stream tests | Keep old implementation path |
| FA-007 | Strengthen relational constraints/session cleanup | Medium | 4 | Not Started | Session deletion contract tests | Keep manual cleanup fallback |
| FA-008 | Document legacy vs graph-native API contracts | Medium | 3 | Not Started | Contract matrix tests | Keep retired endpoints returning 410 |
| FA-009 | Align dependency and Docker packaging | Medium | 1 | Not Started | Docker build/import smoke | Revert ignore/dependency edits |
| FA-010 | Replace mutable JSON defaults | Low/Medium | 1 | Not Started | Two-row default isolation test | Revert model default change |
| FA-011 | Add missing auth/contract coverage | Medium | 3 | Not Started | New tests fail before fix, pass after fix | Revert tests independently |

## Phase Progress

### Phase 0: Safety Preparation

- Status: In Progress
- Goal: Freeze current behavior and make rollback easy.
- Next actions:
  - Create branch.
  - Run full tests.
  - Capture OpenAPI snapshot.
  - Capture Docker build/import baseline.
  - Record critical behavior for sessions, plans, approvals, SSE, DLQ, and metrics.

### Phase 1: Low-Risk Cleanup

- Status: Not Started
- Goal: Reduce repository and deployment noise without changing behavior.
- Candidate changes:
  - Expand `.dockerignore`.
  - Identify whether committed DB/index artifacts are required.
  - Replace mutable JSON defaults.
  - Move pure helper functions from `routes.py` only after tests exist.

### Phase 2: Bug Fixes and Contract Fixes

- Status: Not Started
- Goal: Fix security and data-integrity risks.
- Candidate changes:
  - Add auth to event streams and DLQ read.
  - Define metrics exposure policy.
  - Enforce production config safety.
  - Make plan persistence transactional.

### Phase 3: Test Coverage Improvement

- Status: Not Started
- Goal: Add tests that make refactoring safe.
- Candidate changes:
  - API/OpenAPI contract snapshot.
  - SSE auth and disconnect tests.
  - DLQ and metrics auth tests.
  - Plan persistence rollback tests.
  - Legacy/graph-native compatibility matrix tests.

### Phase 4: Architecture Refactoring

- Status: Not Started
- Goal: Improve locality by separating route, service, and projection responsibilities.
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

Before any code changes:

1. Create a branch.
2. Run full tests.
3. Capture OpenAPI snapshot.
4. Add failing auth/contract tests for exposed endpoints.
5. Fix the smallest issue first.
