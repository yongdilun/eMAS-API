/* eslint-disable react/prop-types */
import { Fragment, useEffect, useRef, useState } from 'react'
import ChatMessage from '../ChatMessage'
import ApprovalCard from './ApprovalCard'
import ExecutionTracker from './ExecutionTracker'
import SessionStatusBanner from './SessionStatusBanner'
import { useFactoryAgentChat } from './useFactoryAgentChat'
import { FACTORY_AGENT_STATUS } from '../../../../services/factoryAgentApi'
import { ApprovalBlocks, ThinkingBlock, ToolBlocks } from '../turns/TurnBlocks'

const statusPillTone = {
  plan_created: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  execution_started: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  tool_result: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  approval_required: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  approval_decided: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  replan_requested: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  session_blocked: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  session_failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  session_completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
}

function PlanSummaryCard({ plan }) {
  if (!plan) return null
  return (
    <div className="mb-3 rounded-xl border border-indigo-200/70 dark:border-indigo-800/40 bg-white dark:bg-gray-800/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-300">
            Active Plan
          </div>
          <div className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
            Version {plan.version}
          </div>
        </div>
        <div className="text-right text-[11px] text-gray-500 dark:text-gray-400">
          <div>{plan.created_by || 'backend'}</div>
          <div className="mt-1 uppercase tracking-wide">
            {(plan.kind || 'execution')} · {(plan.status || 'draft')}
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm text-gray-800 dark:text-gray-100">
        {plan.plan_explanation || 'No plan explanation available.'}
      </p>
      <div className="mt-2 rounded-lg bg-indigo-50/70 dark:bg-indigo-950/20 px-3 py-2 text-xs text-indigo-800 dark:text-indigo-200">
        Risk summary: {plan.risk_summary || 'No risk summary available.'}
      </div>
    </div>
  )
}

function DebugDetails({ session, plan, steps, pendingApproval }) {
  if (!session) return null
  return (
    <details className="mb-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50">
      <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-gray-600 dark:text-gray-300">
        Debug Details
      </summary>
      <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
        <pre className="overflow-x-auto rounded-lg bg-gray-50 dark:bg-gray-950/60 p-3 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify({ session, plan, steps, pendingApproval }, null, 2)}
        </pre>
      </div>
    </details>
  )
}

function EventBlock({
  message,
  pendingApproval,
  approvalReason,
  setApprovalReason,
  decideApproval,
  isDecidingApproval,
}) {
  if (message.eventType === 'approval_required' && pendingApproval?.approval_id === message.approvalId) {
    return (
      <ApprovalCard
        approval={pendingApproval}
        reason={approvalReason}
        onReasonChange={setApprovalReason}
        onApprove={(args) => decideApproval('approve', args)}
        onReject={() => decideApproval('reject')}
        deciding={isDecidingApproval}
      />
    )
  }

  if (!message.eventType || message.eventType === 'user_message') return null

  return (
    <div className="mt-2 rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-gray-50 dark:bg-gray-900/40 p-3 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${statusPillTone[message.eventType] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200'}`}>
          {message.eventType.replaceAll('_', ' ')}
        </span>
        {(message.toolName || message.status) ? (
          <span className="text-[10px] text-gray-500 dark:text-gray-400">
            {[message.toolName, message.status].filter(Boolean).join(' · ')}
          </span>
        ) : null}
      </div>

      {message.eventType === 'tool_result' && message.details?.result ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-gray-600 dark:text-gray-300">Show raw result</summary>
          <pre className="mt-2 overflow-x-auto rounded bg-white dark:bg-gray-950/60 p-2 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify(message.details.result, null, 2)}
          </pre>
        </details>
      ) : null}

      {message.eventType === 'approval_decided' && message.details?.rejection_reason ? (
        <div className="mt-2 rounded-lg bg-red-50 dark:bg-red-950/20 px-2.5 py-2 text-red-700 dark:text-red-300">
          Reason: {message.details.rejection_reason}
        </div>
      ) : null}

      {message.eventType === 'replan_requested' && message.details?.reason ? (
        <div className="mt-2 rounded-lg bg-violet-50 dark:bg-violet-950/20 px-2.5 py-2 text-violet-700 dark:text-violet-300">
          Trigger: {message.details.reason}
        </div>
      ) : null}
    </div>
  )
}

const FactoryAgentChatPanel = ({ onClose, onHeaderMouseDown }) => {
  const chatRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const {
    session,
    plan,
    steps,
    messages,
    turns,
    sessionList,
    activeSessionName,
    input,
    setInput,
    loading,
    isSending,
    isCancelling,
    error,
    pendingApproval,
    approvalReason,
    messageMode,
    setApprovalReason,
    setMessageMode,
    isDecidingApproval,
    isPollingSession,
    isPollingApprovals,
    lastSyncedAt,
    handleSend,
    handleCancel,
	    decideApproval,
	    startNewSession,
	    switchSession,
	    renameSession,
	    deleteSession,
    retryFromCurrent,
  } = useFactoryAgentChat()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [editingSessionId, setEditingSessionId] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [isDeletingSession, setIsDeletingSession] = useState(false)

  useEffect(() => {
    if (!chatRef.current) return
    if (!shouldAutoScrollRef.current) return
    chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [turns, messages, isSending, pendingApproval, session?.status])

  const handleChatScroll = () => {
    if (!chatRef.current) return
    const el = chatRef.current
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    shouldAutoScrollRef.current = distanceToBottom < 120
  }

  useEffect(() => {
    shouldAutoScrollRef.current = true
  }, [session?.session_id])

  const inputDisabled = isSending || session?.status === FACTORY_AGENT_STATUS.PLANNING
  const canCancel = Boolean(session?.session_id) && [FACTORY_AGENT_STATUS.PLANNING, FACTORY_AGENT_STATUS.EXECUTING, FACTORY_AGENT_STATUS.WAITING_APPROVAL, FACTORY_AGENT_STATUS.BLOCKED].includes(session?.status)

  let placeholder = 'Ask factory agent...'
  if (session?.status === FACTORY_AGENT_STATUS.PLANNING) placeholder = 'Planning in progress...'
  if (session?.status === FACTORY_AGENT_STATUS.EXECUTING) placeholder = 'Send a follow-up message for the next replan point...'
  if (session?.status === FACTORY_AGENT_STATUS.WAITING_APPROVAL) placeholder = 'Request a plan change while approval is pending...'

  return (
    <div className="flex h-full relative">
      {deleteTarget ? (
        <div
          className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          role="dialog"
          aria-modal="true"
          aria-label="Delete session confirmation"
          onMouseDown={(e) => {
            // click outside to close
            if (e.target === e.currentTarget && !isDeletingSession) setDeleteTarget(null)
          }}
        >
          <div className="w-full max-w-md rounded-2xl border border-gray-200/80 dark:border-gray-700/80 bg-white dark:bg-[#111618] shadow-2xl p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  Delete session?
                </div>
                <div className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                  This will permanently remove the chat history, plan steps, approvals, and debug timeline for:
                </div>
              </div>
              <button
                type="button"
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
                onClick={() => {
                  if (!isDeletingSession) setDeleteTarget(null)
                }}
                aria-label="Close"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <div className="mt-3 rounded-xl bg-amber-50/80 dark:bg-amber-900/15 border border-amber-200/70 dark:border-amber-800/40 px-3 py-2">
              <div className="text-xs font-semibold text-amber-900 dark:text-amber-200 truncate">
                {deleteTarget.name || deleteTarget.session_id}
              </div>
              <div className="mt-0.5 text-[11px] text-amber-800/80 dark:text-amber-200/80">
                Session ID: {deleteTarget.session_id}
              </div>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={isDeletingSession}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-60"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeletingSession}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
                onClick={async () => {
                  setIsDeletingSession(true)
                  try {
                    const ok = await deleteSession(deleteTarget.session_id)
                    if (ok) setDeleteTarget(null)
                  } finally {
                    setIsDeletingSession(false)
                  }
                }}
              >
                {isDeletingSession ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <aside
        className={`${sidebarCollapsed ? 'w-14' : 'w-72'} border-r border-gray-200/80 dark:border-gray-700/80 bg-white dark:bg-[#111618] transition-all duration-200 flex flex-col`}
      >
        <div className="px-2.5 py-2 border-b border-gray-200/70 dark:border-gray-700/70 flex items-center gap-2">
          {!sidebarCollapsed ? (
            <>
              <button
                type="button"
                onClick={startNewSession}
                className="flex-1 px-2.5 py-2 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90"
              >
                New Session
              </button>
              <button
                type="button"
                onClick={() => setSidebarCollapsed(true)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
                aria-label="Collapse sessions"
              >
                <span className="material-symbols-outlined text-lg">left_panel_close</span>
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setSidebarCollapsed(false)}
              className="w-full p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
              aria-label="Expand sessions"
            >
              <span className="material-symbols-outlined text-lg">left_panel_open</span>
            </button>
          )}
        </div>

        {!sidebarCollapsed ? (
          <div className="overflow-y-auto p-2 space-y-1">
            {sessionList.length === 0 ? (
              <div className="px-2 py-3 text-xs text-gray-500 dark:text-gray-400">
                No sessions yet.
              </div>
            ) : (
              sessionList.map((item) => {
                const isActive = item.session_id === session?.session_id
                const isEditing = editingSessionId === item.session_id
                return (
                  <div
                    key={item.session_id}
                    className={`group rounded-lg border ${isActive ? 'border-primary/50 bg-primary/5' : 'border-gray-200/70 dark:border-gray-700/70 bg-transparent'}`}
                  >
                    <button
                      type="button"
                      onClick={() => switchSession(item.session_id)}
                      className="w-full text-left px-2.5 py-2"
                    >
                      {isEditing ? (
                        <input
                          autoFocus
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onBlur={() => {
                            renameSession(item.session_id, editingName)
                            setEditingSessionId(null)
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              renameSession(item.session_id, editingName)
                              setEditingSessionId(null)
                            }
                            if (e.key === 'Escape') {
                              setEditingSessionId(null)
                            }
                          }}
                          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-sm text-gray-900 dark:text-gray-100"
                        />
                      ) : (
                        <div className="flex items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                              {item.name}
                            </div>
                            <div className="mt-0.5 text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
                              {item.status || FACTORY_AGENT_STATUS.IDLE}
                            </div>
                          </div>
	                          <span
	                            role="button"
	                            tabIndex={0}
	                            onClick={(e) => {
	                              e.preventDefault()
	                              e.stopPropagation()
	                              setEditingSessionId(item.session_id)
	                              setEditingName(item.name || '')
	                            }}
	                            onKeyDown={(e) => {
	                              if (e.key === 'Enter' || e.key === ' ') {
	                                e.preventDefault()
	                                e.stopPropagation()
	                                setEditingSessionId(item.session_id)
	                                setEditingName(item.name || '')
	                              }
	                            }}
	                            className="material-symbols-outlined text-base text-gray-500 dark:text-gray-400 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
	                          >
	                            edit
	                          </span>
	                          <span
	                            role="button"
	                            tabIndex={0}
	                            onClick={(e) => {
	                              e.preventDefault()
	                              e.stopPropagation()
	                              setDeleteTarget(item)
	                            }}
	                            onKeyDown={(e) => {
	                              if (e.key === 'Enter' || e.key === ' ') {
	                                e.preventDefault()
	                                e.stopPropagation()
	                                setDeleteTarget(item)
	                              }
	                            }}
	                            className="material-symbols-outlined text-base text-gray-500 dark:text-gray-400 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
	                            aria-label="Delete session"
	                            title="Delete session"
	                          >
	                            delete
	                          </span>
	                        </div>
	                      )}
                    </button>
                  </div>
                )
              })
            )}
          </div>
        ) : null}
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200/80 dark:border-gray-700/80 bg-white dark:bg-[#111618]">
          <div
            className="flex items-center gap-3 cursor-move select-none flex-1 min-w-0"
            onMouseDown={onHeaderMouseDown}
            data-drag-handle
            role="presentation"
          >
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {activeSessionName || 'Factory Agent Chat'}
            </h2>
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-600 dark:text-sky-400 text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
              {session?.status || 'Ready'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {canCancel && (
              <button
                type="button"
                onClick={handleCancel}
                disabled={isCancelling}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-60 dark:bg-amber-900/30 dark:text-amber-300"
              >
                {isCancelling ? 'Cancelling...' : 'Cancel'}
              </button>
            )}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
                aria-label="Close"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="px-4 py-2 bg-amber-50/80 dark:bg-amber-900/15 border-b border-amber-200/60 dark:border-amber-800/40 text-sm text-amber-700 dark:text-amber-400">
            {error}
          </div>
        )}

        <div ref={chatRef} onScroll={handleChatScroll} className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50 dark:bg-gray-900/60">
          <SessionStatusBanner session={session} onRetry={retryFromCurrent} />
          <ExecutionTracker
            session={session}
            lastSyncedAt={lastSyncedAt}
            isPollingSession={isPollingSession}
            isPollingApprovals={isPollingApprovals}
          />
          <PlanSummaryCard plan={plan} />
          <DebugDetails session={session} plan={plan} steps={steps} pendingApproval={pendingApproval} />

          {loading && (turns?.length || 0) === 0 && messages.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-400 text-sm">
              Loading...
            </div>
          ) : (turns?.length || 0) === 0 && messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center px-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-primary">smart_toy</span>
              </div>
              <p className="text-gray-700 dark:text-gray-300 text-sm font-medium">
                Start a session from the sidebar.
              </p>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-1.5">
                Ask for operations tasks requiring safe approvals.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-4">
                {[
                  'Check machine 5 status',
                  'Update machine 5 to maintenance',
                  'Show pending approvals',
                ].map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                    disabled={inputDisabled}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {(turns || []).map((turn) => {
                const hasApprovalCard =
                  pendingApproval &&
                  Array.isArray(turn.approvals) &&
                  turn.approvals.some((a) => a?.event_type === 'approval_required' && a?.approval_id === pendingApproval.approval_id)

                const passiveApprovals = Array.isArray(turn.approvals)
                  ? turn.approvals.filter((a) => {
                    if (a?.event_type === 'approval_required' && pendingApproval?.approval_id === a?.approval_id) return false
                    if (a?.event_type === 'approval_decided' && String(a?.status || '').toUpperCase() === 'APPROVED') return false
                    return true
                  })
                  : []

                const userTs = turn.user?.created_at
                  ? new Date(turn.user.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : null
                const assistantTs = turn.created_at
                  ? new Date(turn.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : null

                return (
                  <Fragment key={turn.id}>
                    {turn.user?.content ? (
                      <ChatMessage message={turn.user.content} isUser timestamp={userTs} />
                    ) : null}
                    <ChatMessage
                      message=""
                      isUser={false}
                      timestamp={assistantTs}
                      messageAfterBlocks
                      renderBlocks={() => (
                        <>
                          <ThinkingBlock items={turn.thinking} />
                          <ToolBlocks tools={turn.tools} />
                          <ApprovalBlocks approvals={passiveApprovals} />
                          {hasApprovalCard ? (
                            <ApprovalCard
                              approval={pendingApproval}
                              reason={approvalReason}
                              onReasonChange={setApprovalReason}
                              onApprove={(args) => decideApproval('approve', args)}
                              onReject={() => decideApproval('reject')}
                              deciding={isDecidingApproval}
                            />
                          ) : null}
                          {turn.summary ? (
                            <div className="mt-2 whitespace-pre-wrap break-words text-gray-900 dark:text-gray-100">
                              {turn.summary}
                            </div>
                          ) : null}
                        </>
                      )}
                    />
                  </Fragment>
                )
              })}

              {messages
                .filter((m) => String(m.id || '').startsWith('optimistic-') && m.role === 'user')
                .map((m) => (
                  <ChatMessage key={m.id} message={m.content} isUser timestamp={m.timestamp} />
                ))}
            </>
          )}

          {isSending && (
            <ChatMessage
              message=""
              isUser={false}
              timestamp={new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              renderBlocks={() => (
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <span className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                  <span className="text-sm">Working...</span>
                </div>
              )}
            />
          )}
        </div>

        <form
          className="mx-4 mt-2 mb-4 p-3 bg-white dark:bg-[#1b2528] shadow-sm rounded-xl border border-gray-200/80 dark:border-gray-700/80 flex items-center gap-2 flex-shrink-0"
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
        >
          <select
            value={messageMode}
            onChange={(e) => setMessageMode(e.target.value)}
            disabled={inputDisabled}
            className="h-11 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 px-3 text-xs text-gray-900 dark:text-white"
            aria-label="Message mode"
          >
            <option value="normal">Normal</option>
            <option value="plan">Plan</option>
          </select>
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            disabled={inputDisabled}
            className="flex-1 resize-none rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
          />
          <button
            type="submit"
            disabled={inputDisabled || !input.trim()}
            className="h-11 w-11 shrink-0 rounded-lg bg-primary text-white flex items-center justify-center disabled:opacity-60 hover:bg-primary/90 transition-colors"
            aria-label="Send"
          >
            {isSending ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <span className="material-symbols-outlined text-xl">send</span>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default FactoryAgentChatPanel
