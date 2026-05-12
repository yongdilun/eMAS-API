# LangGraph Architecture Migration Plan

This document outlines the exact migration plan to transition the `factory_agent` to the production-ready stateful LangGraph architecture as specified.

## 1. Architectural Alignment
The goal is to shift from a custom-orchestrated router/planner (`QueryRouter` and `ExecutionEngine`) to a LangGraph-native state machine. 
- **Current State:** `ExecutionEngine` manually manages session state, Database rows, and tool routing via `QueryRouter`. 
- **Target State:** LangGraph `AgentState` acts as the single source of truth. The planner is the "brain", tools are "dumb" nodes, and checkpoints handle recovery.

## 2. Files to be Changed and Logic to be Cleaned

1. **`factory_agent/graph/state.py`**
   - **Clean:** Remove old `AgentState` fields (`pending_tool_call`, `draft`, `raw_plan`).
   - **Change:** Implement the new comprehensive state schema (`original_query`, `intents`, `current_intent`, `retrieved_info`, `tool_outputs`, `decisions`, `approval_requests`, `validation_results`, `checkpoint_history`, `errors`, `status`).

2. **`factory_agent/orchestration/router.py`**
   - **Clean:** Deprecate `QueryRouter` and its heavy weighted-scoring system (`API_ONLY`, `RAG_ONLY`, `API_THEN_RAG`).
   - **Change:** Transition routing logic entirely into the Intent Splitter layer.

3. **`factory_agent/planning/intent.py`**
   - **Clean:** Remove basic regex-based `assess_intent` logic.
   - **Change:** Implement a lightweight Intent Splitter that consumes the raw query and outputs structured intents (e.g., `[{"type": "machine_lookup", "need": {...}}]`).

4. **`factory_agent/graph/builder.py` & `factory_agent/graph/planner_graph.py`**
   - **Clean:** Re-wire the `StateGraph`. Remove the simple `prepare -> reason -> validate` flow.
   - **Change:** Build the new graph with: 
     - Input Layer -> Intent Splitter
     - Planner Loop (iterating over `current_intent`)
     - Tool Execution Nodes (with parallel execution support)
     - Final Validator

5. **`factory_agent/graph/nodes/` (New/Updated)**
   - **Change:** Implement `planner_node` (evaluates state, selects tools/actions), `tool_execution_node` (executes dumb tools, returns structured results), and `final_validator_node`.

6. **`factory_agent/orchestration/execution.py`**
   - **Clean:** Strip out custom DB-based plan execution, step looping, and manual state tracking (`SessionRow`, `PlanRow`, `PlanStepRow` updates during execution).
   - **Change:** Adapt this to act as the LangGraph checkpoint saver, persisting graph state after major steps to enable partial rollbacks.

7. **`factory_agent/services/planner_service.py`**
   - **Clean:** Move deduplication and provenance logic into the respective LangGraph nodes (either Planner or Tool nodes).

---

## 3. Migration Phases

### Phase 1: State Schema & Core Types Migration
**Goal:** Establish the LangGraph state as the single source of truth.
- **Tasks:**
  - Update `AgentState` in `graph/state.py` to include all required fields: `original_query`, `messages`, `intents`, `current_intent`, `retrieved_info`, `tool_outputs`, `completed_actions`, `staged_writes`, `failed_strategies`, `decisions`, `approval_requests`, `validation_results`, `errors`, `status`. (Note: `checkpoint_history` is removed as it is natively handled by LangGraph's checkpointer).
  - Specify LangGraph reducers for the state fields:
    - `messages` must use the `add_messages` reducer.
    - Trace and list fields (`intents`, `tool_outputs`, `completed_actions`, `staged_writes`, `failed_strategies`, `errors`) must use `Annotated[list[T], operator.add]` to allow appending.
    - Current execution fields (`current_intent`, `status`, etc.) should use the default overwrite reducer.
  - Refactor data models in `schemas.py` if necessary to support the new state object.
- **Exit Requirement:** The new `AgentState` can be initialized, passed through a dummy LangGraph node, and type-checks successfully pass across the codebase.

### Phase 2: Intent Understanding Layer
**Goal:** Decompose multi-task requests without executing tools or reasoning.
- **Tasks:**
  - Deprecate `QueryRouter` in `orchestration/router.py`.
  - Build a lightweight intent splitter (using LLM or rule-based) in `planning/intent.py`. This splitter must be "dumb"—it only extracts intents into JSON (e.g., `{"type": "fix_machine"}`) and does *not* validate completeness or trigger fast-fail clarifications.
  - The splitter must explicitly parse an `explicit_constraints` array into a richer constraint model. Any parameter explicitly demanded by the user (e.g., "Use Machine M-001") must be strictly logged using the following schema:
    ```python
    class ExplicitConstraint(BaseModel):
        field: str
        operator: Literal["=", "!=", "<", "<=", ">", ">=", "in", "not_in", "before", "after", "prefer"] = "="
        value: Any
        source_text: str | None = None
        strength: Literal["hard", "soft"] = "hard"
        mutable: bool = False

    class Intent(BaseModel):
        intent_id: str
        description: str
        depends_on: list[str] = Field(default_factory=list)
        explicit_constraints: list[ExplicitConstraint] = Field(default_factory=list)
        status: Literal["pending", "in_progress", "waiting_clarification", "waiting_approval", "completed", "failed", "cancelled", "cancelled_due_to_dependency_failure"] = "pending"
        failure_reason: str | None = None
        category: Literal["scheduling", "inventory", "machine", "job", "reporting", "general", "unknown"] = "unknown"
    ```
    The `category` provides a lightweight semantic grouping for UI or routing priority, without being tool-specific.
  - Create the `InputLayer` and `IntentSplitter` nodes in `graph/builder.py` that populate the `intents` list in `AgentState`.
- **Exit Requirement:** A complex multi-part user query (e.g., "Find available CNC machines and schedule job 001") is successfully parsed into distinct, structured intents, complete with `depends_on` relationships and `explicit_constraints`, and stored in the state. Incomplete queries are also parsed as-is without rejection.

### Phase 3: Planner Node & Graph Re-wiring
**Goal:** Implement the "brain" of the system.
- **Tasks:**
  - Create the `PlannerNode` that reads the `AgentState`.
  - Implement a dynamic execution model using a **hybrid approach**: Native LLM tool-calling for action selection + A structured `PlannerDecision` envelope for routing metadata. The LLM invokes tools natively (including Control Tools like `request_clarification(question)`, `mark_intent_completed(summary)`), and the `PlannerNode` normalizes this raw `AIMessage` into a strict `PlannerDecision` object:
    ```python
    class PlannerDecision(BaseModel):
        decision_id: str
        intent_id: str
        kind: Literal["domain_tool", "parallel_read_tools", "request_clarification", "request_approval", "intent_completed", "intent_failed", "halt"]
        tool_calls: list[ToolCall] = []
        control_action: ControlAction | None = None
        decision_summary: str # Short rationale/explanation for observability
        risk_level: Literal["read", "write_dry_run", "write_commit", "high_risk"] = "read"
        violates_constraints: bool = False
    ```
  - Update `graph/builder.py` to establish a tight, continuous loop: `Planner -> DecisionGuard -> Tool Execution -> Planner`. After every tool execution, the graph loops back to the Planner to observe the new state and decide the next step.
  - **Pre-Execution Guard (`DecisionGuard`):** Implement a guard that runs immediately after the LLM generates tool arguments. It programmatically checks proposed arguments against `explicit_constraints`. If a violation is found, it sets `violates_constraints=True`, skips the tool execution entirely, and instantly triggers an auto-repair loop back to the Planner.
  - **Sequential Processing & Dependency Queue:** Multi-intent requests are processed sequentially using a strict queue. If an intent reaches terminal failure, the Planner automatically marks all downstream dependent intents as `cancelled_due_to_dependency_failure`. The graph halts unless the remaining intents are explicitly independent and allowed to continue. This prevents cascading execution based on missing or invalid prior results.
  - Implement a rolling execution trace in the state (e.g., `completed_actions`) to provide frontend observability without needing a fixed upfront plan.
  - Centralize clarification logic here: if the Planner sees an incomplete intent from the Intent Splitter, it officially transitions to a "request clarification" node.
- **Exit Requirement:** The Planner node dynamically guides the workflow step-by-step, respects inter-intent dependencies and halts on cascade failures, successfully loops, adapts to failed or unexpected tool results on the fly, and maintains a clear execution trace in the state.

### Phase 4: Tool Execution & State Store Integration
**Goal:** Refactor tools into dumb functions and handle parallel execution.
- **Tasks:**
  - Extract tool execution logic from `ExecutionEngine` into pure LangGraph tool nodes.
  - Implement **Two-Phase Commit (Staging Mode) with Simulated State** for write tools. Write tools must *never* execute physical changes during the main planning loop.
  - **Transaction-Scoped References:** To enable same-turn dependent write chaining, the system supports client-side transaction-scoped references (e.g., `$ref:create_job_1`) instead of waiting for backend mock IDs.
    - The LLM may propose these symbolic refs in a single `AIMessage` to chain dependent actions (e.g., `create_job` and `assign_machine` together).
    - The `PlannerNode` (or DecisionGuard) must normalize and validate these refs before staging them.
    - The payloads and their `output_ref` are appended to the `staged_writes` array.
  - **Bundle Dry-Run Validation:** Prefer bundle dry-runs over sequential dependent dry-runs. The graph should batch the staged writes and perform a bundle dry-run against the backend. The backend registers these refs only inside the transaction context to validate dependencies safely.
  - Implement an atomic `CommitNode` at the very end of the graph. After the `FinalValidatorNode` successfully passes the intent, the `CommitNode` must not execute staged writes as separate REST calls. To guarantee atomicity, the backend must expose a unified transaction-bundle commit endpoint (e.g., `POST /agent/transaction/commit`). The `CommitNode` sends the full `staged_writes` array to this endpoint, and the backend executes the bundle inside a single database transaction, resolving operation refs to real IDs atomically and rolling back all writes if any operation fails.
  - Implement **semantic deterministic idempotency hashing** for write tools within the `CommitNode`. The node must compute a hash: `sha256(session_id + intent_id + action_id + tool_name + canonical_json(args) + write_generation)`. 
  - The node logs this `idempotency_key` into the state (for auditing) and explicitly passes it as a header to the backend API.
  - *Backend Requirement:* The backend API must enforce this key. Exact matches return the cached response; key matches with different args must be rejected with `HTTP 409 Idempotency key conflict`.
  - Implement a distinct `RelevanceFilterNode` that executes immediately after tool nodes. LLM relevance checking is **opt-in, not default**, to avoid latency and token bloat. The node applies the following rules:
    - **Obvious empty results (e.g., 404, `[]`):** Deterministic code-based fail (`useful: false`).
    - **Direct lookups / Dry-run responses:** Fast pass-through (`useful: true`).
    - **Bulk structured data:** Code-based filtering/ranking.
    - **RAG / noisy semantic data:** Mandatory semantic filtering (LLM/reranker) whenever the tool's metadata explicitly declares `requires_semantic_filter: true`.
    - **Infrastructure error:** Bypass relevance entirely and halt.
    This node updates the state with the usefulness flag *before* control returns to the Planner.
  - Ensure read tool outputs are written strictly to `AgentState["tool_outputs"]` and `AgentState["retrieved_info"]`.
- **Exit Requirement:** Tool nodes execute actions deterministically and safely. Write tools never create dangling side-effects during replans because they only stage data. The `CommitNode` generates stable semantic idempotency keys and executes writes only after full validation.

### Phase 5: Checkpointing, Failure Recovery & Final Validation
**Goal:** Ensure production readiness with partial rollbacks and safety validations.
- **Tasks:**
  - Completely remove the legacy custom execution tracking models (`SessionRow`, `PlanRow`, `PlanStepRow`, etc.) from the persistence layer.
  - Implement LangGraph's native checkpointer (e.g., `AsyncPostgresSaver`) to save the graph state after every successful major step.
  - **Explicit Distinction: Checkpoint Rollback vs. Logical Auto-Repair:**
    - *Infrastructure Recovery:* LangGraph's native checkpointer is used exclusively for resuming execution after a hard crash or a user interrupt (e.g., waiting for Approval).
    - *Logical Auto-Repair (Forward-Moving State):* Never erase failed business attempts during auto-repair. If validation or a commit fails, the node routes forward back to the Planner. It must explicitly append the failure to `failed_strategies`, clear `staged_writes`/`tool_outputs` to compact the state, and invalidate stale plan data, preventing amnesia and oscillating loops.
  - Implement `FinalValidatorNode` and Approval mechanics using **native LangGraph interrupts**. For high-risk write actions, the graph will formally pause, freezing the deterministic state.
  - Implement **Post-Execution Validation** inside the `FinalValidatorNode`. Since `DecisionGuard` already handles pre-execution constraints, this node focuses on outcomes:
    1. **Domain Validation (Primary):** Use bundle dry-run evidence to ensure business logic validity and confirm that backend side-effects match expectations.
    2. **Policy-Triggered Semantic Check:** The `FinalValidatorNode` is always mandatory, but LLM semantic verification is executed only when the intent's policy or category explicitly requires qualitative judgment. When triggered, the LLM evaluator deterministically scores the final state against the original intent, routing to auto-repair if it fails.
  - The API will resume execution by injecting the user's approval response directly into the interrupted checkpoint, bypassing the need for the Planner to "re-reason" the action.
  - Implement a **controlled auto-repair loop** within the FinalValidatorNode. If validation fails, the node routes back to the Main Planner. Set a strict limit of `max_repair_attempts = 3`.
  - Introduce a `failed_strategies` array in the `AgentState`. Upon validation failure, the FinalValidator explicitly logs the failed approach here (a "graveyard" of negative constraints). The Planner is strictly instructed to read this array and never repeat a failed strategy, preventing oscillating loops.
  - Implement **Rigid Constraint Tracking** during replans. The Planner is strictly forbidden from substituting any parameter listed in the `explicit_constraints` array from Phase 2. If an explicit constraint causes the failure, the Planner must halt the repair loop and explicitly request clarification from the user.
  - Implement **Intelligent Error Routing**. The Tool Execution Node must distinguish between logical errors (e.g., HTTP 4XX) and infrastructure failures (e.g., HTTP 5XX, timeouts). System failures must write a `FATAL_SYSTEM_ERROR` to the state. The FinalValidator is hardcoded to *never* trigger an auto-repair loop if a fatal error is present, immediately halting the graph instead.
  - Implement **Commit-Time Failure Handling**: If the `CommitNode` encounters a business-logic error (e.g., `409 Conflict`), it must perform a full transaction rollback, log the failure into `failed_strategies`, and route back to the Main Planner for auto-repair. The repaired plan *must* go through the `FinalValidatorNode` and the user Approval interrupt again. If the `CommitNode` encounters an infrastructure error, it triggers a `FATAL_SYSTEM_ERROR` and halts immediately.
  - Implement **State Truncation (Garbage Collection)** during replans. Before routing back to the Planner, the FinalValidator must clear the raw, bulky `tool_outputs` generated during the failed attempt, leaving only concise summaries in the execution trace. This prevents context window bloat and "lost in the middle" degradation.
- **Exit Requirement:** The system demonstrates partial recovery without custom DB logic. Validation failures successfully trigger auto-repair replanning loops without oscillation, without context bloat, and strictly respecting user constraints. Fatal infrastructure errors bypass replanning entirely and safely halt execution.

### Phase 6: API and UI Alignment (Pure LangGraph Transition)
**Goal:** Align the API boundaries and Frontend UI with the new native LangGraph state structure.
- **Tasks:**
  - Implement a **Backend Event Adapter** that watches the internal LangGraph stream and computes state diffs.
  - Rewrite backend API endpoints to stream **Semantic Server-Sent Events (SSE)** (e.g., `PLANNER_THINKING`, `TOOL_STARTED`, `APPROVAL_REQUIRED`) to the frontend.
  - **State Hydration Pattern:** The backend must expose a `GET /agent/sessions/{session_id}/snapshot` endpoint. The frontend must hydrate from this snapshot before opening the SSE stream. On any reconnect, the frontend must re-fetch the snapshot, then resume SSE. This keeps the UI consistent during browser refreshes, network drops, approval pauses, and backend restarts.
  - The Phase 6 contract is strictly defined as:
    - *LangGraph checkpoint* = Internal execution truth
    - *Snapshot endpoint* = Frontend recovery truth
    - *Semantic SSE* = Frontend live update stream
  - Refactor frontend components (e.g., `FactoryAgentChatPanel.jsx`) to listen to these semantic SSE events and build a local UI state for rendering tools, approvals, and thinking steps, rather than parsing raw LangGraph blobs.
- **Exit Requirement:** The React frontend successfully renders the end-to-end execution flow by hydrating from the snapshot and consuming Semantic SSE events, completely decoupled from the internal raw LangGraph state and legacy relational data structures.
