/**
 * @typedef {Object} SessionResponse
 * @property {string} session_id
 * @property {string} user_id
 * @property {'IDLE'|'PLANNING'|'WAITING_APPROVAL'|'EXECUTING'|'BLOCKED'|'FAILED'|'COMPLETED'} status
 * @property {string|null} [current_intent]
 * @property {string|null} [plan_id]
 * @property {number} [plan_version]
 * @property {string|null} [plan_hash]
 * @property {number} [current_step_index]
 * @property {number} [step_count]
 * @property {number} [replan_count]
 * @property {number} [llm_call_count]
 * @property {Object|null} [replan_context]
 * @property {string|null} [pending_user_message]
 * @property {string|null} [error]
 */

/**
 * @typedef {Object} MessageResponse
 * @property {string} message_id
 * @property {string} session_id
 * @property {'user'|'assistant'|'system'|'tool_result'} role
 * @property {string} content
 * @property {string} created_at
 */

/**
 * @typedef {Object} PlanResponse
 * @property {string} plan_id
 * @property {string} session_id
 * @property {number} version
 * @property {string} plan_hash
 * @property {string|null} [plan_explanation]
 * @property {string|null} [risk_summary]
 */

/**
 * @typedef {Object} ApprovalResponse
 * @property {string} approval_id
 * @property {string} session_id
 * @property {string} step_id
 * @property {string} tool_name
 * @property {Object} args
 * @property {string} risk_summary
 * @property {'NONE'|'LOW'|'MEDIUM'|'HIGH'|'CRITICAL'} side_effect_level
 * @property {'PENDING'|'APPROVED'|'REJECTED'|'EXPIRED'} status
 * @property {string} expires_at
 * @property {string|null} [rejection_reason]
 */

/**
 * @typedef {Object} PlanStepResponse
 * @property {string} step_id
 * @property {string} session_id
 * @property {number} step_index
 * @property {string} tool_name
 * @property {Object} args
 * @property {'NOT_STARTED'|'IN_PROGRESS'|'DONE'|'FAILED'|'SKIPPED'|'AMBIGUOUS'} status
 * @property {Object|null} [result]
 * @property {string|null} [result_summary]
 * @property {string|null} [last_error]
 */

export {}
