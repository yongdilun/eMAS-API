# Playwright E2E Replacement Plan

Created: 2026-05-16

Branch: `codex/playwright-e2e-plan`

Scope: planning only. Do not delete or replace the existing E2E/manual pipeline until Phase 7.

## Current-State Analysis

### Repository Shape

This repo is not a single app package. The relevant parts are:

| Area | Path | Role |
|---|---|---|
| React frontend | `eMas Front/` | Vite/React browser UI. The visible chatbot is the Factory Agent chat modal. |
| Go backend | `emas/` | Gin API, seeded E2E server, legacy `/api/v1/ai/chats` chatbot routes, scheduling and approval APIs. |
| Factory Agent | `factory-agent/` | FastAPI service used by the current frontend chat panel. Owns session, message, plan, execute, snapshot, approval, and SSE routes. |
| Existing E2E contracts | `tests/e2e/` | Seed manifest, PowerShell runner, Promptfoo config, and Python HTTP scenario runner. |
| RAG eval harness | `tests/rag_eval/` | Opt-in live LLM/RAG structural evaluation. |

### Existing E2E / Manual Testing Approach

Current coverage is mostly API and component level:

- `tests/e2e/run_seed_pipeline.ps1` orchestrates Go `internal/e2e` tests, Factory Agent pytest checks, seeded Go API startup, optional real Factory Agent API scenarios, and artifacts under `test-artifacts/`.
- `emas/internal/e2e/*` covers seeded Go API behavior and chatbot approval driver flows.
- `factory-agent/tests/*` covers FastAPI routes, snapshots, approvals, event stream runtime, planner behavior, reliability, RAG, and contracts.
- `eMas Front/package.json` has `npm test`, but it uses Node's built-in test runner plus jsdom/Vite SSR helpers for component and utility tests. It does not drive a real browser.
- `eMas Front/scripts/factory-agent-smoke.js` drives Factory Agent over HTTP, but not through the browser.
- `factory-agent/FRONTEND_PHASE0_BASELINE.md` documents manual/browser observations and screenshots from prior frontend baseline work.
- `eMas Front/playwright-report/` exists as an artifact, but there is no Playwright dependency, config, or test script in `eMas Front/package.json`.

There is no root `package.json`, no root `.github/` CI workflow, and no current automated browser E2E pipeline.

### Existing Test Tools and Scripts

| Tool | Current Use | Notes |
|---|---|---|
| Go `go test` | Go unit, handler, router, and seeded E2E tests | Includes `emas/cmd/e2e_server` for seeded local API startup. |
| Pytest | Factory Agent route, planner, snapshot, SSE, RAG, and reliability tests | Root `pytest.ini` disables pytest cache provider. |
| Node `--test` | Frontend component and utility tests in jsdom | Good for rendering regressions, not browser behavior. |
| Promptfoo | `tests/e2e/promptfoo.seed-pipeline.yaml` | LLM intent smoke harness, opt-in. |
| Manual browser checks | Recorded in `factory-agent/FRONTEND_PHASE0_BASELINE.md` and screenshots | This is the gap to replace. |

### Current Chatbot Flow

The primary user-facing chatbot flow is the React Factory Agent modal:

1. `eMas Front/src/App.jsx` renders `FloatingChatButton`.
2. Clicking it opens `AIAssistantModal`.
3. `AIAssistantModal` renders `FactoryAgentChatPanel`.
4. `FactoryAgentChatPanel` uses `useFactoryAgentChat`.
5. `useFactoryAgentChat` creates or restores a Factory Agent session, sends user messages, creates plans, executes sessions, refreshes snapshots, and receives EventSource updates.
6. `FactoryAgentChatComposer` provides the message mode select, textarea, send button, and cancel button.
7. Final visible assistant responses are assembled from Factory Agent snapshot timeline data by `turnAssembler` and rendered by `ChatMessage` / `StreamedAssistantText`.

Important nuance: the current backend SSE does not stream token-by-token assistant text. The actual SSE streams are notification/activity/semantic streams that invalidate snapshots and send activity steps. The final answer is snapshot-derived, then the frontend animates the visible text locally.

The legacy Go chatbot flow still exists:

- Frontend client wrapper: `eMas Front/src/services/api.js` under `aiApi.chats`.
- Backend routes: `emas/internal/handler/ai_chat_handler.go` under `/api/v1/ai/chats`.
- Phase 0 chatbot service: `emas/internal/service/chatbot_service.go`.

The visible React chat panel currently targets Factory Agent, so Playwright should start there and keep legacy Go chat coverage as a separate optional track.

### Frontend Entry Points

Primary files:

- `eMas Front/src/main.jsx`
- `eMas Front/src/App.jsx`
- `eMas Front/src/components/shared/FloatingChatButton.jsx`
- `eMas Front/src/components/features/chat/AIAssistantModal.jsx`
- `eMas Front/src/components/features/chat/factory-agent/FactoryAgentChatPanel.jsx`
- `eMas Front/src/components/features/chat/factory-agent/FactoryAgentChatComposer.jsx`
- `eMas Front/src/components/features/chat/factory-agent/useFactoryAgentChat.js`
- `eMas Front/src/components/features/chat/factory-agent/useSessionEvents.js`
- `eMas Front/src/components/features/chat/factory-agent/useActivityStream.js`
- `eMas Front/src/services/factoryAgentApi.js`

Current selector risk: the floating chat button has visible text only on hover and no `aria-label`. Phase 1 should add a stable accessible label or `data-testid` before relying on it.

### Backend / API / SSE Entry Points

Factory Agent REST:

- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `POST /sessions/{session_id}/messages`
- `GET /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/plans`
- `POST /sessions/{session_id}/execute`
- `GET /sessions/{session_id}/snapshot`
- `GET /sessions/{session_id}/steps`
- `POST /sessions/{session_id}/confirm`
- `POST /sessions/{session_id}/cancel`
- `GET /approvals/pending`
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject`

Factory Agent SSE:

- `GET /sessions/{session_id}/events`
  - Notification-only stream.
  - Emits `notification` frames such as `hello`, `snapshot_invalidated`, `phase_changed`, and `heartbeat`.
- `GET /sessions/{session_id}/events/activity`
  - User-facing activity stream.
  - Emits `control` frames such as `STREAM_READY`, `SESSION_NOT_FOUND`, `HEARTBEAT`.
  - Emits `activity` frames with stable activity steps.
- `GET /sessions/{session_id}/events/semantic`
  - Semantic stream derived from snapshot timeline diffs.
  - Not currently consumed by the visible React chat hooks, but it is part of the backend streaming surface.

Relevant backend files:

- `factory-agent/factory_agent/api/routes.py`
- `factory-agent/factory_agent/api/routers/events.py`
- `factory-agent/factory_agent/api/routers/messages.py`
- `factory-agent/factory_agent/api/routers/plans.py`
- `factory-agent/factory_agent/api/routers/execution.py`
- `factory-agent/factory_agent/api/routers/snapshots.py`
- `factory-agent/factory_agent/services/session_snapshot_service.py`
- `factory-agent/main.py`

Go backend / legacy chatbot:

- `emas/internal/router/router.go`
- `emas/internal/handler/ai_chat_handler.go`
- `emas/internal/service/chatbot_service.go`
- `emas/cmd/e2e_server/main.go`

### Auth, Session, and Environment Behavior

- Frontend Factory Agent base URL comes from `VITE_FACTORY_AGENT_BASE_URL`; default is `http://127.0.0.1:8000`.
- Frontend Go API base URL comes from `VITE_API_BASE_URL`; default is `http://localhost:8080/api/v1`.
- Docker uses `/agent` and `/api/v1` through nginx.
- Factory Agent auth is controlled by `JWT_REQUIRED`; development can run with auth disabled.
- `VITE_FACTORY_AGENT_BEARER_TOKEN` causes REST requests to send `Authorization`, but browser `EventSource` cannot set authorization headers. The frontend intentionally disables EventSource and keeps snapshot polling enabled when a static bearer token is configured.
- Go protected scheduling/approval routes can require `X-User-Id` and `X-User-Role`.
- CORS in `factory-agent/main.py` allows local Vite origins by default.

### Pain Points and Risks

- No current automated real-browser coverage for opening chat, typing, submitting, waiting, or asserting final UI state.
- Manual checks are still required to validate the actual chatbot flow.
- Existing smoke/API tests do not prove DOM behavior, loading state, stream diagnostics, accessibility, or cancel/navigation behavior.
- Real LLM/model calls are nondeterministic and should not be used in CI.
- EventSource streams are hard to validate with simple request interception because partial streaming, connection close, and disconnect behavior matter.
- Static bearer auth disables EventSource, so both SSE-enabled and polling-fallback modes need browser coverage.
- SSE unit tests exist in Factory Agent, but browser integration against `EventSource` and UI updates is missing.
- Existing generated `playwright-report/` is not ignored in `eMas Front/.gitignore`.
- No root CI workflow exists to run a Playwright browser suite.
- Docker/Compose startup needs local env values and external LLM config; this is too heavy for a deterministic default browser CI job.

## Target Architecture

### Playwright Test Structure

Keep Playwright owned by the frontend package because the browser app is under `eMas Front/`.

Proposed files:

```text
eMas Front/
  playwright.config.js
  e2e/
    fixtures/
      factoryAgentFixtures.js
      sseScripts.js
      selectors.js
    mock-server/
      factoryAgentMockServer.js
      fixtureStore.js
    specs/
      chat-happy-path.spec.js
      chat-loading-final-state.spec.js
      chat-sse-notification.spec.js
      chat-sse-activity.spec.js
      chat-stream-errors.spec.js
      chat-cancel-navigation.spec.js
    README.md
  test-results/              # ignored
  playwright-report/         # ignored
```

Package scripts:

```json
{
  "test:e2e": "playwright test",
  "test:e2e:headed": "playwright test --headed",
  "test:e2e:debug": "playwright test --debug",
  "test:e2e:report": "playwright show-report"
}
```

### Test Environment Strategy

Default CI/local deterministic job:

- Start Vite through Playwright `webServer`.
- Start a test-only mock Factory Agent HTTP/SSE server through Playwright global setup or a second `webServer`.
- Set `VITE_FACTORY_AGENT_BASE_URL=http://127.0.0.1:<mock-port>`.
- Keep `VITE_API_BASE_URL` pointed at a mock route/server only when approval option lookup requires it.
- Run Chromium in CI first; add Firefox/WebKit only after the suite is stable.

Optional full-stack job:

- Reuse `emas/cmd/e2e_server` for seeded Go API.
- Reuse Factory Agent with a fake planner/model provider or fixture mode.
- Keep this job opt-in or nightly until startup and model substitution are fully deterministic.

### Mocking Strategy

Best strategy for this repo: a test-only mock Factory Agent HTTP/SSE server.

Why:

- The frontend is already isolated behind `VITE_FACTORY_AGENT_BASE_URL`.
- The visible chat flow primarily depends on Factory Agent REST, snapshots, and EventSource streams.
- Browser `EventSource` needs a real HTTP stream to test open, message order, malformed frames, server close, and client disconnect behavior.
- Playwright route interception can mock REST endpoints, but it is a poor fit for timed partial SSE chunks and disconnect assertions.
- MSW is not present, would add a second mocking stack, and service-worker interception is not the most reliable way to test native EventSource behavior.
- A test-only API handler inside production code would increase app surface area for a test concern.
- A controlled fake model provider is still useful later for full-stack Factory Agent tests, but it is not the fastest path to deterministic browser E2E.

Use Playwright route interception only for narrow REST-only cases, such as one-off Go API lookup endpoints or forced HTTP 500 responses.

### SSE Validation Strategy

Use two layers:

1. Browser-facing SSE tests through the mock Factory Agent server.
   - The mock server sends scripted `text/event-stream` frames with delays.
   - It records connection open, last-event-id, close, and disconnect events for assertions.
   - Tests assert DOM behavior: progress bar, diagnostics, activity rows, final answer, cancel button, and final non-busy state.

2. SSE parser/contract tests in Playwright or Node helper code.
   - Parse fixture SSE scripts directly to prove event IDs, event names, data payloads, malformed payload handling, and expected snapshot mutations.
   - Keep Factory Agent backend event runtime tests in pytest as lower-level coverage.

Required SSE scenarios:

- Successful streamed response via notification invalidation plus final snapshot.
- Multiple activity chunks arriving in order.
- Final completion event represented by snapshot `phase`/`status` and terminal timeline event.
- Backend error represented by failed snapshot/timeline state and/or HTTP error on snapshot refresh.
- Network interruption by closing the SSE connection and asserting polling fallback diagnostic.
- Timeout by delaying final snapshot and asserting non-completed state or configured timeout UI.
- Empty response by returning completed session with no assistant summary.
- Malformed event payload by emitting invalid JSON and asserting the UI ignores it without crashing.
- User cancel or navigation away during stream by clicking cancel/close or changing route and asserting EventSource disconnect.

### CI Pipeline Strategy

Add a future root workflow such as `.github/workflows/playwright-e2e.yml` because no root CI workflow currently exists.

Recommended CI steps:

```powershell
cd "eMas Front"
npm ci
npx playwright install --with-deps chromium
npm run test:e2e -- --project=chromium
```

Artifacts:

- Upload `eMas Front/playwright-report/`.
- Upload `eMas Front/test-results/`.
- Keep traces, screenshots, and video only on failure or retry.

Flake controls:

- Use deterministic mock server scripts, not real LLM calls.
- Avoid arbitrary sleeps in tests; wait for locators, network events, mock server state, or DOM status.
- Keep per-test isolated session IDs and fixture state.
- Disable retries locally; allow one retry in CI only after traces are enabled.
- Use a single worker at first for SSE tests, then parallelize when fixture state isolation is proven.

### Data / Fixture Strategy

Fixture data should mirror real snapshot and event shapes from Factory Agent:

- Session fixture: `session_id`, `status`, `phase`, `cursor`, `name`, timestamps.
- Snapshot fixture: `session`, `timeline`, `pending_approval`, `activity_steps`, `resume_hint`, `plan`.
- Message fixture: user and assistant records.
- Event scripts:
  - notification frames with `id`, `event: notification`, and JSON `data`.
  - activity frames with `id`, `event: activity`, and JSON step payload.
  - control frames for readiness, heartbeats, and session-not-found.

Prefer a small number of readable fixture builders over massive static JSON dumps. Reuse seed identifiers such as `M-CNC-01`, `JOB-SEED-001`, and `frontend-operator` where it improves alignment with existing tests.

### Debugging / Reporting Strategy

- Enable Playwright HTML report.
- Use `trace: "on-first-retry"`, `screenshot: "only-on-failure"`, `video: "retain-on-failure"`.
- Capture console errors and failed network responses in a shared fixture.
- Add a mock server request log attachment for failed tests.
- Add `eMas Front/e2e/README.md` with local commands, env vars, and how to inspect reports.

## Long-Term Testing Scope Strategy

The Playwright effort should grow in layers. Each layer should earn its place by catching a different class of risk, not by repeating the same happy path with different prompt text.

### Scope Ladder

| Stage | Name | Main Purpose | Backend Strategy | CI Role | Promotion Gate |
|---|---|---|---|---|---|
| L0 | Browser smoke | Prove the app opens and the chat shell is usable. | Minimal mock Factory Agent. | Required on every PR. | Stable chat-open test and no real services. |
| L1 | Deterministic mocked chat | Cover user-visible chat behavior, final answers, approvals, and errors. | Fixture-driven mock Factory Agent REST. | Required on every PR. | First 12-15 scenarios pass in under 3 minutes. |
| L2 | Deterministic mocked SSE | Cover EventSource lifecycle, ordered chunks, fallback, malformed frames, cancel, and timeout behavior. | Mock Factory Agent REST plus real `text/event-stream`. | Required on every PR once stable; initially one worker. | Full 30-scenario portfolio passes with trace artifacts on failure. |
| L3 | Seeded full-stack browser | Prove frontend contracts against seeded Go API and Factory Agent without real LLM calls. | `emas/cmd/e2e_server` plus Factory Agent fake planner/model provider. | Scheduled or pre-merge gate for release branches. | Same critical scenarios pass against real services and seeded data. |
| L4 | Production-like release validation | Validate Docker/nginx paths, auth mode, polling fallback, and realistic deployment env. | Compose or staging environment with controlled fake model or approved external model. | Release candidate gate. | No critical flow regressions, reports archived. |
| L5 | Production synthetic monitoring | Keep a small safe canary running after release. | Read-only production/staging user and health-safe prompts only. | Post-deploy monitor, not PR CI. | Alerts on availability, latency, SSE/fallback, and final answer completion. |

### Test Pyramid for This Repo

Keep responsibilities separated:

- Go `go test`: backend handlers, routing, seed data, approval contracts, and database behavior.
- Factory Agent pytest: planner/service contracts, snapshot shape, SSE runtime, approval resume, RAG structure, and reliability.
- Frontend Node tests: component rendering and pure UI assembly logic.
- Playwright mocked browser tests: real user flows through the browser with deterministic REST/SSE fixtures.
- Playwright seeded full-stack tests: a smaller release-gate subset proving the browser still matches real service contracts.
- Production synthetic checks: safe read-only availability checks only, never broad destructive scenarios.

### Scenario Selection Rules

Use these rules to keep the first suite meaningful and non-redundant:

- Prefer one scenario per distinct risk: input, loading state, snapshot completion, SSE ordering, fallback, approval, cancellation, error, auth mode, and persistence.
- Do not add prompt variants unless they exercise a different UI state or backend contract.
- Every scenario must name the user-visible assertion and the backend/SSE behavior it proves.
- Default to mocked deterministic data for PR CI.
- Use seeded full-stack only when the scenario needs real routing, nginx, Go API data, or Factory Agent schema compatibility.
- Keep the initial browser suite around 30 scenarios. Add new scenarios by retiring or merging old ones if the suite becomes repetitive.

### First-Wave Scenario Portfolio

These 30 scenarios are the initial target. Implement them gradually across Phases 1-5; do not wait until all 30 are written before getting the first Playwright signal into CI.

| # | Scenario | Primary Risk Covered | Recommended Layer |
|---|---|---|---|
| 1 | App opens dashboard and floating chat control is reachable by an accessible selector. | Browser boot, routing, selector stability. | L0 |
| 2 | Chat modal opens and shows empty state plus enabled composer. | Core entry point and usable input. | L0 |
| 3 | New session can be started from the sidebar. | Session creation UX and REST `POST /sessions`. | L1 |
| 4 | Existing active session is restored from local storage. | Session persistence and initial snapshot load. | L1 |
| 5 | User sends "Show status for machine M-CNC-01" and sees final assistant answer. | Core happy path from input to completed response. | L1 |
| 6 | User asks for low priority jobs and sees a result/table-style answer. | Structured result rendering, not just plain text. | L1 |
| 7 | User asks a RAG/LOTO question and sees answer plus source/citation chrome. | Source rendering and stream-gated extras. | L1 |
| 8 | Follow-up message after completion creates a second distinct turn. | Multi-turn continuity and no stale answer overwrite. | L1 |
| 9 | Plan mode submission preserves mode and produces expected planning/progress copy. | Composer mode path and plan-specific behavior. | L1 |
| 10 | Final assistant text animates to completion before sources/details appear. | Local typewriter behavior and final completed state. | L1 |
| 11 | Notification SSE `hello` opens, invalidates snapshot, and triggers refresh. | EventSource notification contract. | L2 |
| 12 | Multiple notification events update in cursor order without duplicate refreshes. | Ordered stream processing and cursor handling. | L2 |
| 13 | Activity stream emits multiple steps and the activity UI shows them in order. | Activity chunk ordering and timeline display. | L2 |
| 14 | Final completion arrives through SSE plus snapshot and removes busy UI. | Terminal state transition. | L2 |
| 15 | SSE heartbeat frames do not create noisy visible messages. | Heartbeat handling. | L2 |
| 16 | SSE reconnect uses `Last-Event-ID` and does not duplicate prior activity. | Reconnect/resume behavior. | L2 |
| 17 | Static bearer token mode disables EventSource and uses polling fallback. | Auth-mode compatibility. | L2 |
| 18 | Malformed SSE payload is ignored and the next valid event still updates UI. | Stream robustness. | L2 |
| 19 | SSE connection drops and UI shows snapshot polling fallback diagnostic. | Network interruption behavior. | L2 |
| 20 | Plan creation returns 503 and UI shows backend unavailable/error state without fake success. | Backend failure display. | L1 |
| 21 | Execute returns 409 once, UI/backend retries, and final response completes. | Retry/concurrency behavior. | L1 |
| 22 | Snapshot returns session not found and UI recovers to a safe state. | Deleted/stale session handling. | L1 |
| 23 | Active session never reaches terminal state before timeout and UI remains honest. | Timeout/no false completion. | L2 |
| 24 | Completed snapshot has empty assistant content and does not show a stale previous answer. | Empty response handling. | L1 |
| 25 | User cancels an active run and final UI returns to idle/cancelled state. | Cancel path and `POST /cancel`. | L2 |
| 26 | User closes modal or navigates during an active stream and EventSource disconnects. | Client disconnect cleanup. | L2 |
| 27 | Approval-required response renders risk summary, preview/table, and Approve/Reject actions. | Approval UI and pending state. | L1 |
| 28 | Approval approve flow resumes and reaches completed final answer. | Approval decision/resume behavior. | L2/L3 |
| 29 | Approval reject flow returns to idle with rejection state and no fake completion. | Rejection handling. | L2/L3 |
| 30 | Confirmation-required flow shows choices, user selects one, and follow-up execution completes. | `WAITING_CONFIRMATION` branch and `/confirm`. | L2/L3 |

### Growth Beyond the First 30

After the first portfolio is stable, expand only where new production risk exists:

- Add seeded full-stack browser coverage for one read-only prompt, one RAG prompt, one approval approve flow, and one cancel flow.
- Add Docker/nginx path checks for `/agent` and `/api/v1` routing.
- Add one production-like static bearer token test to prove polling fallback.
- Add performance budgets for chat-open time, first progress indication, and completed answer latency.
- Add accessibility checks for the chat modal controls once selectors are stable.
- Add visual regression only for stable UI surfaces such as the empty state, approval card, and final answer card.
- Add production synthetic monitoring only for safe read-only prompts and health checks.

## Phased Implementation Plan

### Phase 0: Discovery and Risk Mapping

Goal:

Document the current testing, frontend chat, backend/API/SSE, auth/session, and environment shape before adding Playwright.

Files likely to be touched:

- `PLAN.md`
- `TRACK.md`

Implementation steps:

- Inspect project layout, package files, tests, chat UI, Factory Agent routes, Go routes, env config, Docker/nginx config, and existing docs.
- Record current-state analysis and risks.
- Create `TRACK.md` with phase status, blockers, decisions, commands, and next action.

Acceptance criteria:

- `PLAN.md` contains repo-specific current state and target architecture.
- `TRACK.md` identifies Phase 1 as the next executable step.
- No implementation code, dependency, or test pipeline changes are made.

Verification command:

```powershell
git status --short --branch
```

Risks or unknowns:

- Some prior manual/browser baseline evidence may be stale.
- No CI provider was found in the repo.

Rollback notes:

- Revert `PLAN.md` and `TRACK.md`.

### Phase 1: Playwright Setup and Baseline Browser Tests

Goal:

Install Playwright and prove the React app can open in a real browser with a deterministic mock backend.

Files likely to be touched:

- `eMas Front/package.json`
- `eMas Front/package-lock.json`
- `eMas Front/playwright.config.js`
- `eMas Front/e2e/README.md`
- `eMas Front/e2e/specs/app-shell.spec.js`
- `eMas Front/e2e/mock-server/factoryAgentMockServer.js`
- `eMas Front/.gitignore`
- Possibly `eMas Front/src/components/shared/FloatingChatButton.jsx`

Implementation steps:

- Add `@playwright/test` as a dev dependency.
- Add `test:e2e`, `test:e2e:headed`, `test:e2e:debug`, and `test:e2e:report` scripts.
- Add Playwright config with Vite `webServer`.
- Add a minimal mock Factory Agent server returning empty sessions and health responses.
- Set `VITE_FACTORY_AGENT_BASE_URL` for Playwright runs.
- Add a baseline test that opens `/`, verifies the app shell, opens the AI Assistant, and verifies the composer is visible.
- Add an accessible label or stable test id to the floating chat button if needed.
- Ignore Playwright reports and test results.
- Cover scenarios 1-2 from the first-wave portfolio.

Acceptance criteria:

- `npm run test:e2e -- --project=chromium` launches Vite, opens the app, and passes a baseline browser test.
- Existing `npm test` remains unchanged and passing.
- No real Factory Agent, Go backend, Docker, or LLM dependency is required.

Verification command:

```powershell
Set-Location "eMas Front"
npm test
npm run test:e2e -- --project=chromium
```

Risks or unknowns:

- Current chat button lacks a stable accessible label.
- Vite env injection must happen before the frontend dev server starts.

Rollback notes:

- Remove Playwright dependency, scripts, config, e2e folder, and any selector-only UI change.

### Phase 2: Chatbot Happy-Path E2E Tests

Goal:

Automate the core user journey: open chatbot, type a message, submit it, observe loading/working UI, and assert final visible response.

Files likely to be touched:

- `eMas Front/e2e/specs/chat-happy-path.spec.js`
- `eMas Front/e2e/fixtures/factoryAgentFixtures.js`
- `eMas Front/e2e/fixtures/selectors.js`
- `eMas Front/e2e/mock-server/factoryAgentMockServer.js`

Implementation steps:

- Add fixture state for one session lifecycle:
  - no active session
  - session created
  - user message added
  - plan created
  - execute started
  - snapshot moves from `PLANNING`/`EXECUTING` to `COMPLETED`
- In the browser, click the chat button, type a realistic prompt, and submit.
- Assert the user message appears optimistically or after snapshot refresh.
- Assert progress/loading UI appears while the session is active.
- Assert final assistant answer content appears.
- Assert the progress indicator is gone and the composer is enabled at completion.
- Cover scenarios 3-10 from the first-wave portfolio where practical.

Acceptance criteria:

- Browser test covers input through final streamed/snapshot-derived response.
- Assertions use user-visible roles/text where possible, with stable fallback selectors only where needed.
- Test does not call real LLM or real Factory Agent.

Verification command:

```powershell
Set-Location "eMas Front"
npm run test:e2e -- --project=chromium --grep "happy path"
```

Risks or unknowns:

- Current UI has client-side typewriter behavior for final answer; tests must wait for completed visible text, not only snapshot state.
- Some current buttons rely on icon-only text and may need accessible labels.

Rollback notes:

- Remove the happy-path spec and fixtures.

### Phase 3: Deterministic Mocking for Chatbot Responses

Goal:

Make chatbot browser tests deterministic, readable, and extensible across multiple scenarios.

Files likely to be touched:

- `eMas Front/e2e/mock-server/factoryAgentMockServer.js`
- `eMas Front/e2e/mock-server/fixtureStore.js`
- `eMas Front/e2e/fixtures/factoryAgentFixtures.js`
- `eMas Front/e2e/fixtures/sseScripts.js`
- `eMas Front/e2e/specs/chat-fixtures.spec.js`
- `eMas Front/e2e/README.md`

Implementation steps:

- Introduce named scenarios such as `readMachineHappyPath`, `ragAnswerWithSources`, `approvalRequired`, `backendUnavailable`, and `emptyCompletedAnswer`.
- Implement per-test fixture reset endpoint or in-process reset hook on the mock server.
- Support deterministic request logs and scenario assertions.
- Support REST errors for `/plans`, `/execute`, and `/snapshot`.
- Keep fixture shapes close to Factory Agent `SessionSnapshotResponse` and timeline events.
- Document how to add a new scenario.

Acceptance criteria:

- Tests can select a scenario without copy-pasting endpoint handlers.
- Mock server logs requests and EventSource lifecycle.
- Fixture builders are small enough for future agents to understand quickly.

Verification command:

```powershell
Set-Location "eMas Front"
npm run test:e2e -- --project=chromium --grep "fixture"
```

Risks or unknowns:

- Fixture drift from real Factory Agent schemas can create false confidence.
- Mitigate by adding a later contract check that validates key fixture fields against existing Factory Agent schema/tests.

Rollback notes:

- Revert mock-server fixture framework and keep only the Phase 2 happy-path mocks.

### Phase 4: SSE Streaming Tests

Goal:

Validate the actual browser SSE behavior for Factory Agent notification and activity streams.

Files likely to be touched:

- `eMas Front/e2e/fixtures/sseScripts.js`
- `eMas Front/e2e/specs/chat-sse-notification.spec.js`
- `eMas Front/e2e/specs/chat-sse-activity.spec.js`
- `eMas Front/e2e/specs/chat-sse-final-state.spec.js`
- `eMas Front/e2e/mock-server/factoryAgentMockServer.js`

Implementation steps:

- Add mock SSE script runner that writes valid `text/event-stream` frames with controlled delays.
- Test successful notification stream:
  - `hello`
  - `snapshot_invalidated`
  - `phase_changed`
  - final completed snapshot
- Test activity stream order:
  - `STREAM_READY`
  - multiple `activity` frames in order
  - final activity state
- Assert visible activity/progress UI updates in order.
- Assert final assistant response only appears after completed snapshot.
- Assert `Last-Event-ID` handling where the browser reconnects.
- Cover scenarios 11-19 and 25-26 from the first-wave portfolio.

Acceptance criteria:

- Multiple chunks/events arriving in order are verified.
- Final completion state is verified in the DOM.
- Mock server proves EventSource connections opened and closed as expected.

Verification command:

```powershell
Set-Location "eMas Front"
npm run test:e2e -- --project=chromium --grep "SSE"
```

Risks or unknowns:

- Playwright cannot directly inspect native EventSource message callbacks from outside the page unless instrumented.
- Use DOM assertions plus mock server connection logs; add optional page instrumentation only if needed.

Rollback notes:

- Remove SSE specs and mock stream runner changes.

### Phase 5: Failure, Timeout, Retry, and Disconnect Scenarios

Goal:

Cover the failure modes currently handled manually or by lower-level tests.

Files likely to be touched:

- `eMas Front/e2e/specs/chat-stream-errors.spec.js`
- `eMas Front/e2e/specs/chat-timeouts.spec.js`
- `eMas Front/e2e/specs/chat-cancel-navigation.spec.js`
- `eMas Front/e2e/mock-server/factoryAgentMockServer.js`
- `eMas Front/e2e/fixtures/sseScripts.js`
- Possibly `eMas Front/src/components/features/chat/factory-agent/*` if missing states or selectors are discovered

Implementation steps:

- Test backend error:
  - `/plans` or `/execute` returns 500/503.
  - UI shows backend unavailable or error diagnostic without fake success.
- Test SSE network interruption:
  - mock server closes stream unexpectedly.
  - UI shows fallback/polling diagnostic.
- Test timeout:
  - snapshot never reaches terminal state within test timeout.
  - UI remains active or displays timeout handling as designed.
- Test empty response:
  - completed snapshot contains no assistant summary.
  - UI does not crash or show stale previous answer.
- Test malformed event payload:
  - invalid JSON frame is ignored.
  - subsequent valid frame still updates UI.
- Test user cancel:
  - active session exposes cancel button.
  - click cancel and assert `/cancel` is called, final state is idle/cancelled.
- Test navigation/close during stream:
  - close modal or navigate away.
  - mock server records EventSource disconnect.
- Cover scenarios 20-24 and 27-30 from the first-wave portfolio.

Acceptance criteria:

- Required failure matrix is covered in browser tests.
- No failure scenario depends on real model/API calls.
- Tests assert user-visible behavior plus mock server request/connection evidence.

Verification command:

```powershell
Set-Location "eMas Front"
npm run test:e2e -- --project=chromium --grep "error|timeout|cancel|disconnect|malformed|empty"
```

Risks or unknowns:

- Some failure states may be handled silently by hooks today, requiring small UI/diagnostic improvements.
- Browser cancel/navigation disconnect timing can be timing-sensitive; use mock server logs with bounded waits.

Rollback notes:

- Remove failure specs and any selector-only UI changes. Keep bug fixes only if separately validated and desired.

### Phase 6: CI Integration

Goal:

Run Playwright browser E2E deterministically in CI with useful artifacts and low flake risk.

Files likely to be touched:

- `.github/workflows/playwright-e2e.yml` or the repo's actual CI config when identified
- `eMas Front/package.json`
- `eMas Front/playwright.config.js`
- `eMas Front/e2e/README.md`
- `.gitignore`

Implementation steps:

- Add CI job using Node 20 or the repo-standard Node version.
- Run `npm ci`.
- Install Playwright Chromium browser with cache-friendly setup.
- Run existing frontend tests first: `npm test`.
- Run Playwright: `npm run test:e2e -- --project=chromium`.
- Upload Playwright report and test results on failure.
- Set workers to `1` initially for SSE tests.
- Use CI retry policy of `1` with traces on retry.
- Keep full-stack/real-service jobs separate and opt-in/nightly.

Acceptance criteria:

- CI runs deterministic browser E2E with no real LLM/API dependency.
- Failure artifacts include report, trace, screenshot, video, and mock server log.
- Existing Go/Python/API pipeline remains intact.

Verification command:

```powershell
Set-Location "eMas Front"
npm ci
npx playwright install chromium
npm test
npm run test:e2e -- --project=chromium
```

Risks or unknowns:

- CI provider is not currently present in the repo.
- Browser cache behavior depends on CI provider.
- Windows vs Linux path handling must be kept portable because local development is on Windows.

Rollback notes:

- Remove the CI workflow/job. Keep local Playwright scripts if useful.

### Phase 7: Cleanup and Replacement of Old Pipeline

Goal:

Deprecate manual chatbot validation and clearly define what remains in the old API/seed pipeline.

Files likely to be touched:

- `tests/e2e/README.md`
- `tests/e2e/run_seed_pipeline.ps1`
- `eMas Front/e2e/README.md`
- `README.md` or `eMas Front/README.md`
- `TRACK.md`
- Existing manual baseline docs if they need deprecation notes

Implementation steps:

- Map old manual checks to new Playwright specs.
- Mark manual chatbot typing/waiting/checking steps as replaced by Playwright.
- Keep `tests/e2e/run_seed_pipeline.ps1` for API contract, seed, reliability, and optional live/full-stack checks.
- Decide whether `factory-agent-smoke.js` remains as a quick API smoke or is replaced by Playwright happy path.
- Update docs with local and CI commands.
- Add a final replacement checklist and owner notes.

Acceptance criteria:

- Future agents know which command replaces manual chatbot validation.
- Old pipeline is not deleted unless there is a proven replacement and explicit approval.
- `TRACK.md` records final decisions, commands, results, and remaining risks.

Verification command:

```powershell
Set-Location "eMas Front"
npm test
npm run test:e2e -- --project=chromium
```

Risks or unknowns:

- Existing API pipeline still covers important non-browser contracts and should not be removed wholesale.
- Live LLM/RAG testing remains opt-in and non-deterministic by design.

Rollback notes:

- Revert documentation deprecation notes and keep old instructions as primary.

## Recommended First Implementation Step

Start with Phase 1:

1. Add `@playwright/test` and Playwright scripts under `eMas Front`.
2. Add a minimal mock Factory Agent server.
3. Add one browser test that opens the app and chat modal.
4. Add a stable accessible selector to the floating chat button if needed.

This creates the smallest real-browser signal without touching the backend, Docker, LLM, or old pipeline.
