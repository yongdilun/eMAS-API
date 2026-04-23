# Factory Operations Agent - Frontend Chatbot Implementation
> Version 2.0 - Backend-aligned (factory-agent current API)
> Updated: April 24, 2026

---

## 0. Purpose

This document defines the frontend implementation that aligns with the current `factory-agent` backend contract.

It replaces older assumptions that are no longer true (for example: SSE stream, `/api/*` prefix, and `first_message` session creation).

Source of truth for this version:
- `factory-agent/agent/api.py`
- `factory-agent/agent/schemas.py`
- `factory-agent/agent/execution.py`
- `factory-agent/main.py`

---

## 1. Key Alignment Decisions

1. Frontend will integrate with the current REST contract first.
2. No SSE is required for v2 (backend does not expose stream endpoints).
3. Live updates are implemented with short polling while executing or waiting approval.
4. Backend remains authoritative for session, plan, approval, and execution state.
5. Existing frontend chat flow (`/ai/chats`, `suggested_calls`) is treated as a separate legacy mode.

---

## 2. Backend API Contract (Current)

Base path: no router prefix in backend (`app.include_router(...)`), so endpoints are:

### 2.1 Sessions

- `POST /sessions`
  - Body: `{ "user_id": string }`
  - Response: `SessionResponse`

- `GET /sessions/{session_id}`
  - Response: `SessionResponse`

- `POST /sessions/{session_id}/messages`
  - Body: `{ "role": "user" | "assistant" | "system" | "tool_result", "content": string }`
  - Response: `MessageResponse`

- `POST /sessions/{session_id}/plans`
  - Body:
    - `{}` to auto-generate with planner, or
    - `{ "draft": PlanDraft }` for client-supplied draft
  - Response: `PlanResponse`

- `POST /sessions/{session_id}/execute`
  - Query:
    - `background` (bool, optional)
    - `expected_version` (int, optional optimistic lock)
  - Response: `SessionResponse`

- `POST /sessions/{session_id}/cancel`
  - Response: `SessionResponse`

### 2.2 Approvals

- `GET /approvals/pending`
  - Response: `ApprovalResponse[]`

- `GET /approvals/{approval_id}`
  - Response: `ApprovalResponse`

- `POST /approvals/{approval_id}/approve`
  - Body: `{ "decided_by"?: string, "rejection_reason"?: string }`
  - Response: `ApprovalResponse`

- `POST /approvals/{approval_id}/reject`
  - Body: `{ "decided_by"?: string, "rejection_reason"?: string }`
  - Response: `ApprovalResponse`

### 2.3 Optional Ops/Admin

- `GET /metrics`
- `GET /admin/*` endpoints (admin key required)
- `GET /dlq`, `POST /dlq/*` (not needed for normal operator chat UX)

---

## 3. Core Data Shapes Used by Frontend

### 3.1 SessionStatus

`IDLE | PLANNING | WAITING_APPROVAL | EXECUTING | BLOCKED | FAILED | COMPLETED`

### 3.2 StepStatus

`NOT_STARTED | IN_PROGRESS | DONE | FAILED | SKIPPED | AMBIGUOUS`

### 3.3 SideEffectLevel

`NONE | LOW | MEDIUM | HIGH | CRITICAL`

### 3.4 Important SessionResponse fields

- `session_id`
- `status`
- `current_intent`
- `plan_id`
- `plan_version`
- `current_step_index`
- `step_count`
- `replan_count`
- `llm_call_count`
- `replan_context`
- `pending_user_message`
- `error`
- `updated_at`

### 3.5 Important ApprovalResponse fields

- `approval_id`
- `session_id`
- `step_id`
- `tool_name`
- `args`
- `risk_summary`
- `side_effect_level`
- `status` (`PENDING | APPROVED | REJECTED | EXPIRED`)
- `rejection_reason`

---

## 4. Frontend Runtime Model (No SSE)

Since there is no `/stream` endpoint, frontend uses polling:

### 4.1 Polling rules

- Poll `GET /sessions/{id}` every 1.5s when:
  - `status == EXECUTING`
  - `status == WAITING_APPROVAL`
  - `status == PLANNING`

- Poll every 4-5s when:
  - `status == BLOCKED`

- Stop polling when:
  - `status == IDLE | FAILED | COMPLETED` and no pending UI action.

- Poll `GET /approvals/pending` every 2s while in `WAITING_APPROVAL`.
  - Filter by `session_id === currentSessionId`.

### 4.2 Reconciliation

On each poll tick:
1. Fetch fresh `SessionResponse`.
2. Update UI state from backend response.
3. If status becomes terminal-ish (`IDLE`, `FAILED`, `COMPLETED`, `BLOCKED`), update banners/actions immediately.
4. If in `WAITING_APPROVAL`, refresh pending approval card from approvals list.

---

## 5. End-to-End User Flow

### 5.1 New request

1. `POST /sessions` with `user_id`.
2. `POST /sessions/{id}/messages` with user text.
3. `POST /sessions/{id}/plans` with empty body (auto planner).
4. `POST /sessions/{id}/execute`.
5. Start polling based on session status.

### 5.2 Approval step

When status becomes `WAITING_APPROVAL`:
1. Fetch pending approval from `GET /approvals/pending` scoped by session.
2. Render approval card (tool, args, risk summary, side effect).
3. Approve: `POST /approvals/{id}/approve`.
4. Reject: `POST /approvals/{id}/reject` with optional `rejection_reason`.
5. Continue polling session until it leaves `WAITING_APPROVAL`.

### 5.3 Cancel

- User clicks cancel:
  - `POST /sessions/{id}/cancel`
- Backend sets unfinished steps to `SKIPPED` and session to `IDLE`.

### 5.4 Mid-execution user message

- `POST /sessions/{id}/messages` with role `user`.
- Backend behavior:
  - During `EXECUTING`: message is queued (`pending_user_message`) and used for replan after current step.
  - During `WAITING_APPROVAL`: can trigger replan path.

---

## 6. UI State Mapping

| Backend status | UI mode | Input | Primary actions |
|---|---|---|---|
| `IDLE` | Ready | Enabled | Send request |
| `PLANNING` | Planning | Disabled | Wait |
| `WAITING_APPROVAL` | Approval needed | Enabled for notes | Approve / Reject / Cancel |
| `EXECUTING` | Running | Enabled (addendum) | Cancel |
| `BLOCKED` | Needs intervention | Enabled | Retry planning flow or cancel |
| `FAILED` | Failed | Enabled | Start new session |
| `COMPLETED` | Done | Enabled | Follow-up or new session |

---

## 7. Error Handling Contract

### 7.1 HTTP errors

- `401`: auth issue -> redirect to login or refresh token flow.
- `404`: missing session/approval -> show "resource no longer exists" and reset local state.
- `409`: optimistic lock/version conflict -> refetch session, retry once.
- `429`: queue/limit exceeded -> show rate limit message and retry option.
- `503`: planner backend unavailable -> show temporary service issue.

### 7.2 Session-level failure UX

- `status == FAILED`: show `session.error` prominently.
- `status == BLOCKED`: show manual intervention guidance and available actions.

### 7.3 Ambiguous execution

If operator-visible details indicate `AMBIGUOUS`, show warning card:
- state may be uncertain
- recommend verification before replay/retry actions

---

## 8. Auth Notes

Backend JWT validation is conditional (`JWT_REQUIRED` env).

Frontend should support bearer token in all calls by default:
- `Authorization: Bearer <token>`

No separate SSE token endpoint is needed for v2.

---

## 9. Frontend Architecture (Recommended)

- React + TypeScript
- Zustand (or Redux Toolkit) for session/approval/polling state
- React Query for request lifecycle and polling
- Axios for HTTP client with auth interceptor

### 9.1 Suggested store slices

- `sessionStore`
  - activeSessionId
  - sessionSnapshot
  - pollMode

- `approvalStore`
  - pendingApprovalsBySession
  - selectedApproval

- `chatStore`
  - messages
  - inputDraft
  - transientSystemNotices

- `uiStore`
  - loading states
  - error banners
  - modal state (cancel confirm)

---

## 10. Migration from Existing Frontend Chat

Current frontend chat uses:
- `/ai/command`
- `/ai/chats`
- `suggested_calls` + `executeSuggestedCall`

To adopt factory-agent flow:

1. Add a new service module `factoryAgentApi` using endpoints in Section 2.
2. Keep legacy `aiApi` path behind feature flag during transition.
3. Introduce a dedicated `FactoryAgentChatPanel` that uses session/plan/execute lifecycle.
4. Switch routes progressively after validation.

---

## 11. Implementation Phases

### Phase 1: API wiring

- Implement `factoryAgentApi` client.
- Build type-safe models from current backend schemas.
- Add auth interceptor and normalized error handling.

### Phase 2: Session lifecycle UI

- Create session + send message + create plan + execute.
- Implement polling controller.
- Render status-driven chat states.

### Phase 3: Approval UX

- Poll pending approvals.
- Render approval card with risk details.
- Approve/reject actions wired.

### Phase 4: Hardening

- Version-conflict retry handling.
- Recovery after refresh.
- Empty/error states and loading behavior.
- Basic integration tests for happy path + approval path + cancel path.

---

## 12. Integration Checklist

- [ ] `POST /sessions` works with `{ user_id }`.
- [ ] Message send updates current intent.
- [ ] Plan creation works with planner-generated draft.
- [ ] Execute transitions through planning/executing states correctly.
- [ ] Polling updates UI without SSE.
- [ ] Pending approval is discoverable via `/approvals/pending`.
- [ ] Approve resumes execution.
- [ ] Reject moves session back to `IDLE` with error reason.
- [ ] Cancel endpoint sets session to `IDLE` and skips pending steps.
- [ ] 401/404/409/429/503 handling is user-friendly.
- [ ] Refreshing page can recover active session view by `session_id`.

---

## 13. Future Enhancement (Optional)

After v2 is stable, add realtime channel as v3:
- SSE or WebSocket server events
- keep REST contract unchanged
- use push to reduce polling frequency

Do not block v2 delivery on realtime transport.

---

*Frontend Implementation v2.0 - aligned to current factory-agent backend contract.*
