/* eslint-disable react/prop-types */
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import ChatMessage from '../ChatMessage'
import ApprovalCard from './ApprovalCard'
import { useFactoryAgentChat } from './useFactoryAgentChat'
import { FACTORY_AGENT_STATUS } from '../../../../services/factoryAgentApi'
import { TablePresentation } from '../turns/TurnBlocks'

const CHAT_VIEW_MODE = (import.meta.env?.VITE_FACTORY_AGENT_CHAT_MODE || 'user').trim().toLowerCase() === 'dev' ? 'dev' : 'user'
const STREAM_BUFFER_MS = Number(import.meta.env?.VITE_FACTORY_AGENT_STREAM_BUFFER_MS || 40)

function dedupeLines(lines = []) {
  const seen = new Set()
  return lines.filter((line) => {
    const normalized = String(line || '').trim()
    if (!normalized || seen.has(normalized)) return false
    seen.add(normalized)
    return true
  })
}

function formatToolName(toolName) {
  return String(toolName || '')
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .trim()
}

function toDeveloperStatus(turn) {
  const terminalType = turn?.terminal?.event_type
  if (terminalType === 'session_completed') return 'Completed'
  if (terminalType === 'session_failed') return 'Failed'
  if (terminalType === 'session_blocked') return 'Blocked'

  const approval = Array.isArray(turn?.approvals) ? turn.approvals[turn.approvals.length - 1] : null
  if (approval?.event_type === 'approval_required') return 'Waiting for approval'

  const lastTool = Array.isArray(turn?.tools) ? turn.tools[turn.tools.length - 1] : null
  if (lastTool?.status === 'FAILED') return 'Request failed'
  if (lastTool?.status === 'DONE') return 'Request completed'
  if (lastTool) return 'Working'
  if (Array.isArray(turn?.thinking) && turn.thinking.length) return 'Thinking'
  return 'Working'
}

function toDeveloperResult(turn) {
  const lastTool = Array.isArray(turn?.tools) ? turn.tools[turn.tools.length - 1] : null
  const result = lastTool?.details?.result
  const lastError = lastTool?.details?.last_error

  if (result?.not_found) return '404 Not Found'
  if (typeof lastError === 'string' && lastError.trim()) return lastError.trim()
  if (typeof lastTool?.status === 'string' && lastTool.status.trim()) return lastTool.status.trim()
  if (turn?.terminal?.event_type === 'session_completed') return 'Completed'
  if (turn?.terminal?.event_type === 'session_failed') return 'Failed'
  if (turn?.terminal?.event_type === 'session_blocked') return 'Blocked'
  return null
}

function buildUserDetailLines(turn) {
  const thinking = Array.isArray(turn?.thinking) ? turn.thinking : []
  const tools = Array.isArray(turn?.tools) ? turn.tools : []
  const approvals = Array.isArray(turn?.approvals) ? turn.approvals : []
  const terminal = turn?.terminal || null

  const lines = []
  const planExplanation = thinking[thinking.length - 1]?.details?.plan_explanation || thinking[thinking.length - 1]?.content
  if (planExplanation && !['Thinking...', 'Working...'].includes(String(planExplanation).trim())) {
    lines.push(planExplanation)
  }

  for (const tool of tools) {
    if (tool?.content && !['Thinking...', 'Working...'].includes(String(tool.content).trim())) {
      lines.push(tool.content)
    }
  }

  for (const approval of approvals) {
    if (approval?.content) lines.push(approval.content)
  }

  if (terminal?.details?.reason) lines.push(`Reason: ${terminal.details.reason}`)
  if (terminal?.details?.rejection_reason) lines.push(`Reason: ${terminal.details.rejection_reason}`)

  return dedupeLines(lines).slice(0, 4)
}

function buildDeveloperDetailLines(turn) {
  const lastTool = Array.isArray(turn?.tools) ? turn.tools[turn.tools.length - 1] : null
  const traceId = lastTool?.step_id || turn?.terminal?.id || turn?.id || null
  const toolLabel = formatToolName(lastTool?.tool_name)

  return dedupeLines([
    `Status: ${toDeveloperStatus(turn)}`,
    toolLabel ? `Tool: ${toolLabel}` : null,
    toDeveloperResult(turn) ? `Result: ${toDeveloperResult(turn)}` : null,
    traceId ? `Trace ID: ${traceId}` : null,
  ])
}

function StreamedAssistantText({ text, streamKey, enabled }) {
  const [displayed, setDisplayed] = useState(enabled ? '' : text)

  useEffect(() => {
    if (!enabled) {
      setDisplayed(text)
      return undefined
    }

    const tokens = String(text || '').match(/\S+\s*/g) || []
    if (!tokens.length) {
      setDisplayed(text)
      return undefined
    }

    let index = 0
    let nextValue = ''
    setDisplayed('')

    const timer = window.setInterval(() => {
      if (index >= tokens.length) {
        window.clearInterval(timer)
        return
      }

      nextValue += tokens[index]
      index += 1
      setDisplayed(nextValue)

      if (index >= tokens.length) {
        window.clearInterval(timer)
      }
    }, Number.isFinite(STREAM_BUFFER_MS) && STREAM_BUFFER_MS > 0 ? STREAM_BUFFER_MS : 40)

    return () => window.clearInterval(timer)
  }, [enabled, streamKey, text])

  return <>{displayed || (enabled ? '' : text)}</>
}

function getLatestToolPresentation(turn) {
  const tools = Array.isArray(turn?.tools) ? turn.tools : []
  for (let index = tools.length - 1; index >= 0; index -= 1) {
    const presentation = tools[index]?.details?.presentation
    if (presentation?.render_hint === 'table' && presentation?.table?.rows?.length) {
      return presentation
    }
  }
  return null
}

function TurnDetails({ mode, turn }) {
  const lines = useMemo(
    () => (mode === 'dev' ? buildDeveloperDetailLines(turn) : buildUserDetailLines(turn)),
    [mode, turn],
  )

  if (!lines.length) return null

  return (
    <details className="mt-3">
      <summary className="cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">
        Show details
      </summary>
      <div className="mt-2 space-y-1 text-xs text-gray-600 dark:text-gray-300">
        {lines.map((line) => (
          <div key={line} className="whitespace-pre-wrap break-words">
            {line}
          </div>
        ))}
      </div>
    </details>
  )
}

function ConfirmationOptions({ turn, onConfirm, disabled }) {
  const [expanded, setExpanded] = useState(false)
  const latest = Array.isArray(turn?.confirmations) ? turn.confirmations[turn.confirmations.length - 1] : null
  const confirmation = latest?.details?.confirmation
  const defaultOptions = Array.isArray(confirmation?.options) ? confirmation.options : []
  const allOptions = Array.isArray(confirmation?.all_options) ? confirmation.all_options : defaultOptions
  const hasMore = confirmation?.has_more === true && allOptions.length > defaultOptions.length
  const visibleOptions = expanded ? allOptions : defaultOptions

  if (!defaultOptions.length) return null

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        {visibleOptions.map((option) => (
          <button
            key={`${option.field}-${option.value}`}
            type="button"
            disabled={disabled}
            onClick={() => onConfirm(option)}
            className="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs font-medium text-primary hover:bg-primary/15 disabled:opacity-60 dark:border-primary/40 dark:bg-primary/15"
          >
            {option.label || `${option.field}: ${option.value}`}
          </button>
        ))}
      </div>
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-primary transition-colors"
        >
          <span className="material-symbols-outlined text-sm">
            {expanded ? 'expand_less' : 'expand_more'}
          </span>
          {expanded ? 'Show fewer fields' : `Show all fields (${allOptions.length})`}
        </button>
      )}
    </div>
  )
}


function AssistantTurnBubble({
  turn,
  timestamp,
  showApprovalCard,
  pendingApproval,
  approvalReason,
  setApprovalReason,
  decideApproval,
  decideConfirmation,
  isDecidingApproval,
  isSending,
  mode,
  shouldAnimateText,
}) {
  const summary = turn?.summary || 'Working...'
  const showDetails = !['Thinking...', 'Working...'].includes(summary)
  const presentation = getLatestToolPresentation(turn)
  const tableAnimKey = `${turn?.id || 'turn'}:${presentation?.table?.total_rows || 0}:${summary}`

  return (
    <ChatMessage
      message=""
      isUser={false}
      timestamp={timestamp}
      renderBlocks={() => (
        <>
          <div className="whitespace-pre-wrap break-words text-gray-900 dark:text-gray-100">
            <StreamedAssistantText
              text={summary}
              streamKey={`${turn?.id || 'turn'}:${summary}`}
              enabled={shouldAnimateText && showDetails}
            />
          </div>
          {presentation ? (
            <TablePresentation
              presentation={presentation}
              animate={shouldAnimateText && showDetails}
              animateKey={tableAnimKey}
            />
          ) : null}
          {showDetails ? <TurnDetails mode={mode} turn={turn} /> : null}
          <ConfirmationOptions turn={turn} onConfirm={decideConfirmation} disabled={isSending} />
          {showApprovalCard ? (
            <div className="mt-3">
              <ApprovalCard
                approval={pendingApproval}
                reason={approvalReason}
                onReasonChange={setApprovalReason}
                onApprove={(args) => decideApproval('approve', args)}
                onReject={() => decideApproval('reject')}
                deciding={isDecidingApproval}
              />
            </div>
          ) : null}
        </>
      )}
    />
  )
}

const FactoryAgentChatPanel = ({ onClose, onHeaderMouseDown }) => {
  const chatRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const {
    session,
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
    handleSend,
    handleCancel,
    decideApproval,
    decideConfirmation,
    startNewSession,
    switchSession,
    renameSession,
    deleteSession,
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
  const canCancel = Boolean(session?.session_id) && [FACTORY_AGENT_STATUS.PLANNING, FACTORY_AGENT_STATUS.EXECUTING, FACTORY_AGENT_STATUS.WAITING_APPROVAL, FACTORY_AGENT_STATUS.WAITING_CONFIRMATION, FACTORY_AGENT_STATUS.BLOCKED].includes(session?.status)
  const mode = CHAT_VIEW_MODE === 'dev' ? 'dev' : 'user'

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
                  This will permanently remove the chat history and approvals for:
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
              {(turns || []).map((turn, index) => {
                const hasApprovalCard =
                  pendingApproval &&
                  Array.isArray(turn.approvals) &&
                  turn.approvals.some((a) => a?.event_type === 'approval_required' && a?.approval_id === pendingApproval.approval_id)

                const userTs = turn.user?.created_at
                  ? new Date(turn.user.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : null
                const assistantTs = turn.created_at
                  ? new Date(turn.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : null
                const isLatestTurn = index === turns.length - 1
                const shouldAnimateText =
                  isLatestTurn &&
                  ![FACTORY_AGENT_STATUS.PLANNING, FACTORY_AGENT_STATUS.EXECUTING, FACTORY_AGENT_STATUS.WAITING_APPROVAL].includes(session?.status)

                return (
                  <Fragment key={turn.id}>
                    {turn.user?.content ? (
                      <ChatMessage message={turn.user.content} isUser timestamp={userTs} />
                    ) : null}
                    <AssistantTurnBubble
                      turn={turn}
                      timestamp={assistantTs}
                      showApprovalCard={hasApprovalCard}
                      pendingApproval={pendingApproval}
                      approvalReason={approvalReason}
                      setApprovalReason={setApprovalReason}
                      decideApproval={decideApproval}
                      decideConfirmation={decideConfirmation}
                      isDecidingApproval={isDecidingApproval}
                      isSending={isSending}
                      mode={mode}
                      shouldAnimateText={shouldAnimateText}
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
              message="Working..."
              isUser={false}
              timestamp={new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
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
