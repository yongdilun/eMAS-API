# Factory Agent Code Practice Rules

Purpose: Rules for this cleanup and future FastAPI/backend work. These rules are meant to preserve behavior while improving maintainability, safety, and testability.

## 1. Change Safety

- Do not rewrite working systems unless a smaller safe path is impossible.
- Prefer small, reversible changes.
- Keep public API paths and response models stable unless a contract change is explicitly approved.
- Before changing behavior, add or identify a test that proves the current behavior.
- Every risky change must have a rollback plan.
- Do not mix cleanup, behavior change, and refactor in the same commit unless they cannot be separated.

## 2. API Contracts

- Every route must have an intentional auth policy.
- Every route must have an explicit request/response contract where practical.
- Do not expose operational data through unauthenticated endpoints.
- SSE endpoints must define:
  - auth method
  - reconnect behavior
  - heartbeat behavior
  - disconnect handling
  - expected client fallback
- Retired endpoints should return explicit status codes and clear messages until consumers are migrated.

## 3. FastAPI Route Design

- Route handlers should be thin.
- Route handlers may:
  - validate request-level inputs
  - call services
  - map known service errors to HTTP errors
  - return response models
- Route handlers should not contain large business flows, graph orchestration, or complex projection logic.
- Group routers by responsibility:
  - sessions
  - messages
  - plans
  - approvals
  - events
  - snapshots
  - admin
- Shared dependencies belong in `factory_agent/api/dependencies.py` or a clearly named dependency module.

## 4. Service and Module Boundaries

- Put business behavior behind service modules with small public interfaces.
- Keep persistence details out of route handlers where practical.
- Keep projection code separate from mutation code.
- Keep graph orchestration separate from HTTP concerns.
- Keep admin behavior separate from user-facing behavior.
- Prefer clear module names over generic utility modules.

## 5. Database and Transactions

- Related writes should be atomic.
- Prefer one transaction for one business operation.
- Use `flush()` when IDs are needed before commit.
- Publish external events only after the database transaction succeeds.
- Do not run production schema mutation implicitly during app startup.
- Use explicit migrations for schema changes.
- Avoid mutable ORM defaults such as `default={}` and `default=[]`; use callables such as `default=dict` and `default=list`.
- Add deletion tests whenever adding session-owned tables.

## 6. Security and Configuration

- Production mode must fail fast if required secrets or auth settings are missing.
- Default admin keys are allowed only for local development.
- JWT-disabled mode is allowed only for local development and isolated tests.
- Metrics exposure must be intentional and documented.
- Tool payloads, approval details, DLQ contents, session timelines, and checkpoint-derived state are sensitive unless proven otherwise.
- Do not rely on CORS as an auth boundary.

## 7. Planner, Graph, and Approval Flow

- Treat LangGraph planner semantics as high-risk.
- Do not change planner routing, checkpointing, approval resume, or commit behavior without regression tests.
- Approval writes must be auditable.
- Approval decision handling must be atomic with visible session state changes.
- Write execution must not happen before validation, dry-run checks, and approval rules pass.
- Preserve graph-native behavior when retiring legacy compatibility behavior.

## 8. Testing Rules

- Add tests before risky fixes when the expected behavior is not already covered.
- Minimum tests for API contract changes:
  - unauthorized request
  - authorized request
  - response shape
  - error shape
  - rollback behavior if writes occur
- Minimum tests for route refactors:
  - OpenAPI diff or endpoint contract snapshot
  - targeted route tests
  - relevant planner/approval regression tests
- Live LLM, Redis, and MySQL tests may remain opt-in, but local unit tests must cover fallback behavior.
- Avoid tests that depend on execution order or shared mutable state.

## 9. Observability

- Log structured events for important lifecycle transitions.
- Avoid logging secrets, JWTs, raw auth headers, or sensitive tool payloads.
- Metrics should measure useful operational behavior:
  - request failures
  - planner failures
  - validation failures
  - approval decisions
  - queue pressure
  - DB pool pressure
  - stream disconnects
- Error logs should include enough context to debug without exposing sensitive payloads.

## 10. Deployment and Packaging

- Keep dependency sources aligned.
- Docker images should not include local databases, logs, caches, scratch files, virtual environments, or accidental vector stores unless explicitly required.
- Docker builds should have a smoke test that imports the app.
- Local development artifacts should be ignored by default.
- Runtime-generated files should not be committed unless they are intentional seeded assets.

## 11. Documentation Rules

- Every architecture cleanup phase must update `FASTAPI_FIX_PROGRESS.md`.
- Any new route auth policy should be documented.
- Any intentional legacy behavior should be documented as active, deprecated, retired, or removed.
- Any production config requirement should be documented near the setting and in operations docs.
- Keep docs factual and tied to files, tests, or observed behavior.

## 12. Review Checklist

Before merging a backend cleanup:

- Did public API behavior stay the same, or is the change documented?
- Are auth requirements explicit?
- Are database writes atomic?
- Are new tests focused and meaningful?
- Did full tests pass?
- Did Docker/import smoke pass if packaging changed?
- Is rollback possible?
- Did the progress tracker get updated?
