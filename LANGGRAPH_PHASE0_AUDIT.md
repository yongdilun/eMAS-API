# LangGraph Migration Phase 0 Audit Baseline

Date: 2026-05-12

Updated: 2026-05-13 reference-check pass; 2026-05-13 Phase 1 schema evidence update; 2026-05-13 Phase 2 intent evidence update; 2026-05-13 Phase 3 planner-loop evidence update

Scope: evidence-only audit of active runtime paths for session creation, message submission, plan creation, execution, approval, snapshot, SSE, checkpointing, and legacy replay. No behavior-changing fixes were made in this pass.

## Executive Status

| Area | Status | Evidence |
| --- | --- | --- |
| Session CRUD | PARTIAL | `SessionRow` is still the public session record and is used by API/UI compatibility paths in `factory-agent/factory_agent/api/routes.py:1307`, `factory-agent/factory_agent/api/routes.py:1320`, `factory-agent/factory_agent/api/routes.py:1332`, and `factory-agent/factory_agent/orchestration/session_manager.py:49`. |
| Message submission | PARTIAL | Messages are persisted as relational `MessageRow` records at `factory-agent/factory_agent/api/routes.py:1472`; user messages can mutate legacy step state or graph approval rows depending on current plan classification. |
| Plan creation | LEGACY STILL USED | `/sessions/{session_id}/plans` calls LangGraph through `PlannerService`, but persists the result as `PlanRow` and `PlanStepRow` compatibility records in `_persist_plan` at `factory-agent/factory_agent/api/routes.py:489`. It also still gates non-operation requests through `assess_intent` at `factory-agent/factory_agent/api/routes.py:1715`. |
| Execution | PARTIAL | `/sessions/{session_id}/execute` routes graph-native sessions to `_run_langgraph_session` at `factory-agent/factory_agent/api/routes.py:2047`, but falls back to `ExecutionEngine.execute_until_blocked` at `factory-agent/factory_agent/api/routes.py:2113` for legacy/current-plan sessions. |
| Approval | PARTIAL | Graph approvals use `subject_type="graph"` and resume via `Command(resume=...)` through `PlannerService.resume_after_approval`, but plan/step approval paths remain active in `factory-agent/factory_agent/api/routes.py:2210` and `factory-agent/factory_agent/api/routes.py:2353`. |
| Snapshot | PARTIAL | `GET /sessions/{session_id}/snapshot` exists at `factory-agent/factory_agent/api/routes.py:1382`, but snapshot data is still assembled primarily from relational session/plan/step/message/event rows with some checkpoint-derived projection. |
| SSE | PARTIAL | Semantic SSE exists at `factory-agent/factory_agent/api/routes.py:1393`, but it polls snapshot timeline diffs rather than streaming directly from graph state changes. |
| Native LangGraph graph | PARTIAL | The compiled graph includes `input_layer -> intent_splitter -> prepare -> planner -> decision_guard -> tool_execution -> relevance_filter -> planner`, plus validation, dry-run, commit, fatal, and clarification nodes in `factory-agent/factory_agent/graph/builder.py:39`. Runtime entry is `graph.ainvoke` at `factory-agent/factory_agent/graph/planner_graph.py:72`. |
| Checkpointing | PARTIAL | Native LangGraph checkpointer is wired in `factory-agent/factory_agent/graph/builder.py:123`, and resume uses `thread_id=session_id` in `factory-agent/factory_agent/graph/planner_graph.py:103`, but legacy memory checkpoints also remain in execution paths. |
| DLQ replay | LEGACY STILL USED | `/dlq/{dlq_id}/replay` is still present at `factory-agent/factory_agent/api/routes.py:2536`; it blocks graph-native sessions but can mutate legacy step sessions. |
| Worker/cold-start recovery | LEGACY STILL USED | `main.py` worker execution still calls `executor.execute_until_blocked` at `factory-agent/main.py:162`; cold-start recovery and event listeners mutate `PlanStepRow`/`SessionRow` at `factory-agent/main.py:184` and `factory-agent/main.py:456`. |
| Frontend chat recovery | PARTIAL | Frontend hydrates from snapshot and opens semantic SSE in `eMas Front/src/components/features/chat/factory-agent/useFactoryAgentChat.js:169` and `eMas Front/src/components/features/chat/factory-agent/useFactoryAgentChat.js:233`; it still calls create-plan then execute in `runIntent` at `eMas Front/src/components/features/chat/factory-agent/useFactoryAgentChat.js:360`. |

## Reference-Check Pass

| Candidate | Reference result | Phase 0 decision |
| --- | --- | --- |
| `ExecutionEngine.execute_until_blocked` | Runtime references remain in `factory-agent/factory_agent/api/routes.py:2113` and `factory-agent/main.py:162`; tests still cover it in `factory-agent/tests/test_execution_engine.py` and `factory-agent/tests/test_approval_resume_integration.py`. | Not safe cleanup. This is active legacy execution and must be retired in a behavior-changing phase. |
| `QueryRouter` / route scores | No active production import of `QueryRouter` was found outside `factory-agent/factory_agent/orchestration/router.py`, but route-score-shaped assumptions remain in tests such as `factory-agent/tests/test_phase5_agent_integration.py:109`. | Approval-gated cleanup. The module is probably removable later, but only after compatibility tests and docs are deliberately rescaled. |
| `assess_intent` | Still used by `/sessions/{session_id}/plans` in `factory-agent/factory_agent/api/routes.py:1716`, `ToolSelector` in `factory-agent/factory_agent/planning/tool_selector.py:570`, and tool scope helpers in `factory-agent/factory_agent/planning/tool_scope.py:80`. | Not safe cleanup. It is compatibility-only by intent, but still active. |
| `SessionRow` | Used across API, session manager, memory manager, worker recovery, and frontend-facing snapshot/session responses. | Keep for UI/history compatibility. |
| `PlanRow` | Used by plan creation, graph-native detection through `created_by="langgraph"`, snapshot projection, approval paths, and legacy execution. | Keep for compatibility projection until graph checkpoint state becomes execution truth. |
| `PlanStepRow` | Used by snapshot steps, legacy execution, cold-start recovery, approval mutations, DLQ replay, and tests. | Keep for legacy and compatibility projection. Not graph-native truth. |
| DLQ replay | `/dlq/{dlq_id}/replay` remains live at `factory-agent/factory_agent/api/routes.py:2536` and event handling remains in `factory-agent/main.py:550`; it explicitly blocks graph-native sessions. | Legacy still used. Keep blocked for graph-native sessions; retire later. |
| Frontend `createPlan -> execute` flow | `useFactoryAgentChat.js` still calls `createPlan` before execute in `runIntent` at line 360 and retry flows at lines 390 and 511. | Behavior-changing to alter. Needs approval before changing UX/API flow. |
| Graph approval detection | Graph sessions are detected through `created_by="langgraph"` and `replan_context.langgraph_pending_approval` at `factory-agent/factory_agent/api/routes.py:292` and `factory-agent/factory_agent/api/routes.py:301`. | Compatibility shim. Keep until graph checkpoint/session metadata replaces it. |

## Phase 1 Evidence Update

Phase 1 confirmed a runtime API schema mismatch from the Phase 0 approval path evidence: graph-native approvals are persisted with `subject_type="graph"` in `factory-agent/factory_agent/api/routes.py:1923`, while the public `ApprovalResponse` contract only accepted `step` and `plan`. The API schema now allows `ApprovalSubjectType = Literal["step", "plan", "graph"]` in `factory-agent/factory_agent/schemas.py:116`; this is a compatibility contract fix, not a legacy behavior retirement.

Phase 1 also confirmed that `AgentState` reducer annotations can initialize and pass through a dummy `StateGraph(AgentState)`. Evidence lives in `factory-agent/tests/test_agent_state.py`, covering `add_messages`, append-only trace reducers, overwrite fields, and the `replace_list()` clear sentinel for clearable buffers.

Verification for this Phase 1 update: `python -m pytest tests/test_agent_state.py`, `python -m pytest tests/test_agent_state.py tests/test_planner_phase3.py tests/test_tool_pipeline.py tests/test_phase5_final_validator.py`, and `python -m compileall factory_agent`.

## Phase 2 Evidence Update

Phase 2 confirmed that graph-native runtime intent understanding is isolated in `factory-agent/factory_agent/graph/nodes/intent_split.py`: `intent_splitter_node` calls `split_user_intents`, then writes the serialized output to `intents`, `working_intents`, `intent_cursor`, and `current_intent` before planner execution. `split_user_intents` in `factory-agent/factory_agent/planning/intent.py` now emits deterministic intent IDs, preserves order-based dependency references for multi-part requests, parses incomplete requests into pending intents, and captures explicit machine, job, product, date, and operator constraints with hard/soft strength.

`assess_intent` remains active in compatibility call sites documented in Phase 0, but it is compatibility-only and delegates to `split_user_intents`. No Phase 0 legacy retirement behavior was changed. `QueryRouter` remains deprecated compatibility code in `factory-agent/factory_agent/orchestration/router.py`, and Phase 2 verification confirmed graph-native code under `factory_agent/graph` does not import `QueryRouter` or route-score fields.

Verification for this Phase 2 update: `python -m pytest tests/test_intent_splitter.py`, `python -m pytest tests/test_intent.py tests/test_intent_splitter.py tests/test_planner_phase3.py tests/test_agent_state.py`, and `python -m compileall factory_agent`.

## Phase 3 Evidence Update

Phase 3 confirmed the graph-native planner loop is active as the execution brain inside the compiled graph for native runs: `Planner -> DecisionGuard -> ToolExecution -> RelevanceFilter -> Planner`, ending in plan synthesis and validation from graph trace state. `factory-agent/tests/test_planner_phase3.py` runs a compiled graph for a multi-intent request and verifies the first guard-blocked tool call is not executed, the repaired call is executed, the second intent proceeds only after the first completes, planner decisions are retained, and `completed_actions` contains planner, guard, tool execution, and relevance trace entries used for final plan synthesis.

Phase 3 also confirmed dependency cancellation behavior in `make_planner_node`: when an upstream intent returns `intent_failed`, pending dependent intents are marked `cancelled_due_to_dependency_failure` with the upstream failure reason. Guard violations now append `failed_strategies` repair entries in addition to `completed_actions`, giving the next planner turn a concrete repair signal without retiring legacy API or frontend plan compatibility paths.

A runtime-path parsing fact discovered during Phase 3 testing updated the Phase 2 evidence: plural `jobs` was being parsed as a hard `job_id="S"` constraint, which caused correct guard behavior to block a normal `list jobs` read. `factory-agent/factory_agent/planning/intent.py` now requires a word boundary after singular `job` before extracting a job ID, and `factory-agent/tests/test_intent_splitter.py` covers that plural-list case. This is a graph-input correctness fix, not a Phase 0 legacy retirement.

Verification for this Phase 3 update: `python -m pytest tests/test_planner_phase3.py tests/test_intent_splitter.py`, `python -m pytest tests/test_agent_state.py tests/test_intent.py tests/test_intent_splitter.py tests/test_planner_phase3.py tests/test_tool_pipeline.py tests/test_phase5_final_validator.py`, and `python -m compileall factory_agent`.

## Runtime Path Classification

| Runtime path | Classification | Notes |
| --- | --- | --- |
| `POST /sessions` | Compatibility | Creates `SessionRow` for public session identity/history. |
| `POST /sessions/{id}/messages` | Compatibility with legacy branches | Persists `MessageRow`; cancellation/replan behavior still edits `PlanStepRow` for non-LangGraph plans and graph approval rows for graph-native sessions. |
| `POST /sessions/{id}/plans` | Compatibility / legacy projection | Uses LangGraph planner when no client draft is supplied, but produces relational `PlanRow`/`PlanStepRow` as the public artifact. |
| `POST /sessions/{id}/execute` with no current plan | Graph-native | Calls `_run_langgraph_session`, which invokes LangGraph and persists compatibility rows after completion. |
| `POST /sessions/{id}/execute` with LangGraph-created plan or graph pending approval | Graph-native with compatibility projection | `_is_graph_native_session` detects `created_by="langgraph"` or `replan_context.langgraph_pending_approval`. |
| `POST /sessions/{id}/execute` with non-LangGraph plan | Legacy | Calls `ExecutionEngine.execute_until_blocked`. |
| `GET /sessions/{id}/snapshot` | Compatibility projection | API recovery truth exists, but not yet purely graph-state-derived. |
| `GET /sessions/{id}/events/semantic` | Compatibility adapter | Emits semantic event names from snapshot timeline polling. |
| `POST /approvals/{id}/approve` for `subject_type="graph"` | Graph-native approval resume | Calls `planner.resume_after_approval(session_id, approved=True)`. |
| `POST /approvals/{id}/reject` for `subject_type="graph"` | Graph-native approval resume | Calls `planner.resume_after_approval(session_id, approved=False)`. |
| `POST /approvals/{id}/approve/reject` for `subject_type="plan"` | Compatibility | Plan approval rows remain supported. |
| `POST /approvals/{id}/approve/reject` for `subject_type="step"` | Legacy | Disabled for graph-native sessions, still active for legacy sessions. |
| `POST /dlq/{id}/replay` | Legacy | Explicitly blocks graph-native sessions but mutates legacy step state. |
| Worker queue in `main.py` | Legacy | Background workers still execute relational plans through `ExecutionEngine`. |

## Behavior-Changing Fixes Requiring Approval

1. Stop frontend `runIntent` from always creating a relational plan before execute; this changes the public workflow and should be approved before implementation.
2. Disable or reroute worker queue execution for graph-native sessions; `main.py` currently assumes `ExecutionEngine`.
3. Replace `/plans` as execution truth with a graph-only run endpoint or make it a pure preview/projection API.
4. Make snapshot/SSE derive from graph checkpoint state instead of relational `PlanStepRow` timeline projection.
5. Retire legacy step approval mutation and DLQ replay for graph-native sessions beyond the current guardrails.
6. Remove `QueryRouter`, route scoring, and legacy planner tests only after reference checks confirm graph-native runtime no longer imports or depends on them.

## Safe Cleanup

No safe cleanup was performed in this pass. Reference checks found no proven-dead helper/import/comment that is both migration-relevant and risk-free to remove. The obvious cleanup candidates are either active runtime paths, compatibility projections, or test-covered legacy behavior.

Validation for this pass was reference-check only:

- `rg` checks for `ExecutionEngine`, `execute_until_blocked`, `QueryRouter`, route scores, `assess_intent`, `PlanRow`, `PlanStepRow`, DLQ replay, graph approval shims, and frontend `createPlan -> execute`.
- No unit tests were run because no runtime code changed.

## Phase 0 Exit Gap

Phase 0 audit evidence is now sufficient to start Phase 1 planning. Phase 0 should not be marked fully complete until the team approves the behavior-changing retirement list or accepts that no safe cleanup is available in this phase.
