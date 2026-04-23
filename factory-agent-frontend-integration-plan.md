# Factory Agent Frontend Integration Plan
> Version 3.0 - Practical implementation plan for current system
> Date: April 24, 2026

---

## 1. Objective

Build a production-ready chatbot frontend that integrates with the existing system without breaking current flows.

This plan combines:
- useful UX ideas from the original frontend chatbot spec (clear approval UX, execution visibility, safe operator actions)
- real backend constraints from current `factory-agent` endpoints
- migration strategy from current `eMas Front` chat (`/ai/command`, `/ai/chats`, `suggested_calls`)

---

## 2. Non-Negotiable Constraints

1. Backend is source of truth for session, approvals, and execution state.
2. Do not block delivery on SSE/WebSocket; use REST + polling first.
3. Preserve existing frontend chat until new flow is verified.
4. Keep risky actions approval-gated and explicit in UI.
5. No hidden auto-write operations from frontend.

---

## 3. Current-State Snapshot

### 3.1 Existing frontend mode (already live)

Current chat logic in `eMas Front` is based on:
- `/ai/command`
- `/ai/chats/*`
- `suggested_calls` + optional auto-run for read-only calls

This remains available as `legacy mode` during migration.

### 3.2 Target factory-agent mode

Target mode uses current `factory-agent` endpoints:
- `POST /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/plans`
- `POST /sessions/{session_id}/execute`
- `POST /sessions/{session_id}/cancel`
- `GET /approvals/pending`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject`

---

## 4. Product Design (What user sees)

### 4.1 Main operator surfaces

1. Conversation pane
- user and assistant bubbles
- system status notices (planning, executing, blocked, completed)

2. Approval card (critical)
- tool name
- arguments preview
- risk summary
- side effect level badge (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- approve and reject controls
- optional rejection reason input

3. Execution tracker
- current step index
- running/failed/skipped/ambiguous indicators
- session-level status banner

4. Safety controls
- cancel session with confirmation
- no blind write execution

### 4.2 Session status to UI mapping

- `IDLE`: input enabled, ready for new request
- `PLANNING`: input disabled with planning status
- `WAITING_APPROVAL`: approval card visible, polling approvals
- `EXECUTING`: execution tracker visible, allow cancel
- `BLOCKED`: intervention banner + retry/cancel guidance
- `FAILED`: error banner + restart action
- `COMPLETED`: success summary + follow-up input

---

## 5. Frontend Technical Architecture

### 5.1 Modules

1. `factoryAgentApi` (new)
- typed wrappers for all factory-agent endpoints

2. `useFactoryAgentChat` (new)
- orchestration hook for session lifecycle
- polling controller
- approval action handlers

3. `FactoryAgentChatPanel` (new)
- new UI component tree for target mode

4. `legacyAiChat` (existing)
- keep untouched behind feature flag

### 5.2 Recommended state slices

- `sessionState`
  - `sessionId`
  - `snapshot`
  - `status`
  - `lastError`

- `approvalState`
  - `pendingApproval`
  - `isSubmittingDecision`

- `chatState`
  - `messages`
  - `inputDraft`
  - `systemNotices`

- `runtimeState`
  - `isPollingSession`
  - `isPollingApprovals`
  - `lastSyncedAt`

---

## 6. Request Lifecycle (Implementation Sequence)

### 6.1 New request

1. Create session: `POST /sessions` with `user_id`
2. Add user message: `POST /sessions/{id}/messages`
3. Create plan: `POST /sessions/{id}/plans` (empty body for auto planner)
4. Start execution: `POST /sessions/{id}/execute`
5. Begin polling loop

### 6.2 Polling strategy (v1 transport)

- Poll `GET /sessions/{id}` every 1.5s while `PLANNING`, `WAITING_APPROVAL`, `EXECUTING`
- Poll every 4s while `BLOCKED`
- Stop polling in steady `IDLE`, `FAILED`, `COMPLETED`
- When `WAITING_APPROVAL`, poll `GET /approvals/pending` every 2s and select by `session_id`

### 6.3 Approval flow

- Approve: `POST /approvals/{approval_id}/approve`
- Reject: `POST /approvals/{approval_id}/reject` (include `rejection_reason` when operator gives one)
- Continue session polling until status changes

### 6.4 Cancel flow

- Confirm cancellation in UI
- Call `POST /sessions/{id}/cancel`
- Show "completed steps are not rolled back" notice

---

## 7. Error and Recovery Design

### 7.1 HTTP mapping

- `401`: auth failure; refresh token or redirect login
- `404`: missing session/approval; clear local pointer and notify user
- `409`: version conflict; refetch session and retry once
- `429`: queue/limit full; show retry-after guidance
- `503`: planner/backing service unavailable; retry action button

### 7.2 Session-level handling

- `FAILED`: show `session.error` + "start new session"
- `BLOCKED`: show intervention guidance + "retry from current" and "cancel"

### 7.3 Ambiguous step handling

When uncertain execution is detected in returned status context:
- show explicit warning card
- advise manual verification
- avoid auto-assuming success

---

## 8. Migration Strategy (No Big-Bang)

### Phase A - Parallel implementation

- Implement new `factoryAgentApi`
- Add new `FactoryAgentChatPanel` route/component
- Keep old chat intact

### Phase B - Internal validation

- QA runs scripted scenarios for approvals, rejections, cancel, blocked, failed
- Compare behavior with backend logs

### Phase C - Controlled rollout

- Feature flag per user group
- Start with internal operators
- Expand gradually

### Phase D - Consolidation

- Merge best UX pieces from legacy chat if needed
- retire old path only after parity and reliability are proven

---

## 9. Detailed Build Checklist

### 9.1 API and types

- [x] Add `factoryAgentApi` service file
- [x] Add typed response contracts (implemented via JSDoc typedefs in JS runtime)
- [x] Add centralized error normalizer

### 9.2 Hook and state

- [x] Implement `useFactoryAgentChat` lifecycle hook
- [x] Implement polling start/stop guard logic
- [x] Add approval lookup by `session_id`

### 9.3 UI components

- [x] Build `FactoryAgentChatPanel`
- [x] Build `ApprovalCard`
- [x] Build `ExecutionTracker`
- [x] Build `SessionStatusBanner`
- [x] Build `CancelConfirmModal`

### 9.4 Flow wiring

- [x] Wire "Send" to create-session -> message -> plan -> execute
- [x] Wire approve/reject actions
- [x] Wire cancel action
- [x] Wire blocked/failed/completed transitions

### 9.5 Testing

- [x] Unit-level validation helpers implemented (error and mode modules)
- [x] Integration smoke script added: `npm run factory-agent-smoke` (happy/approval/reject/cancel)
- [x] Manual test support implemented: page refresh recovery with active session and local cache restore

---

## 10. Acceptance Criteria

System is ready when all are true:

1. Operator can complete full request lifecycle without manual API calls.
2. Approval-required steps always require explicit operator decision.
3. Status transitions are visible and stable in UI.
4. Cancel behavior is clear and safe.
5. Blocked and failed states are actionable, not silent.
6. Legacy chat remains available until rollout is approved.

---

## 11. Optional Next Step (Post-Stabilization)

After rollout stability:
- add SSE/WebSocket push channel to reduce polling
- keep same REST endpoints for command/actions
- treat push as optimization, not redesign

---

## 12. Suggested File Plan (Frontend)

- `eMas Front/src/services/factoryAgentApi.ts`
- `eMas Front/src/components/features/chat/factory-agent/useFactoryAgentChat.ts`
- `eMas Front/src/components/features/chat/factory-agent/FactoryAgentChatPanel.tsx`
- `eMas Front/src/components/features/chat/factory-agent/ApprovalCard.tsx`
- `eMas Front/src/components/features/chat/factory-agent/ExecutionTracker.tsx`

---

This plan is designed to be implementable in your current codebase with minimal disruption and clear rollback safety.
