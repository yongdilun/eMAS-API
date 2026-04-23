import { useEffect, useRef, useState } from 'react'
import ChatMessage from '../ChatMessage'
import ApprovalCard from './ApprovalCard'
import ExecutionTracker from './ExecutionTracker'
import SessionStatusBanner from './SessionStatusBanner'
import { useFactoryAgentChat } from './useFactoryAgentChat'
import { FACTORY_AGENT_STATUS } from '../../../../services/factoryAgentApi'

const FactoryAgentChatPanel = ({ onClose, onHeaderMouseDown }) => {
  const chatRef = useRef(null)
  const {
    session,
    messages,
    sessionList,
    activeSessionName,
    input,
    setInput,
    loading,
    isSending,
    error,
    pendingApproval,
    approvalReason,
    setApprovalReason,
    isDecidingApproval,
    isPollingSession,
    isPollingApprovals,
    lastSyncedAt,
    handleSend,
    decideApproval,
    startNewSession,
    switchSession,
    renameSession,
    retryFromCurrent,
  } = useFactoryAgentChat()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [editingSessionId, setEditingSessionId] = useState(null)
  const [editingName, setEditingName] = useState('')

  useEffect(() => {
    if (!chatRef.current) return
    chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, isSending, pendingApproval, session?.status])

  const inputDisabled = isSending || session?.status === FACTORY_AGENT_STATUS.PLANNING

  return (
    <div className="flex h-full relative">
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

        <div ref={chatRef} className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50 dark:bg-gray-900/60">
          <SessionStatusBanner session={session} onRetry={retryFromCurrent} />
          <ExecutionTracker
            session={session}
            lastSyncedAt={lastSyncedAt}
            isPollingSession={isPollingSession}
            isPollingApprovals={isPollingApprovals}
          />

          {pendingApproval ? (
            <ApprovalCard
              approval={pendingApproval}
              reason={approvalReason}
              onReasonChange={setApprovalReason}
              onApprove={() => decideApproval('approve')}
              onReject={() => decideApproval('reject')}
              deciding={isDecidingApproval}
            />
          ) : null}

          {loading && messages.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-400 text-sm">
              Loading...
            </div>
          ) : messages.length === 0 ? (
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
            messages.map((m) => (
              <ChatMessage
                key={m.id}
                message={m.content}
                isUser={m.role === 'user'}
                timestamp={m.timestamp}
                renderBlocks={() => (
                  <>
                    {m.role === 'tool_result' ? (
                      <div className="mt-2 rounded-lg border border-gray-200/70 dark:border-gray-700/70 bg-gray-50 dark:bg-gray-900/40 p-2 text-xs">
                        <div className="font-semibold text-gray-700 dark:text-gray-200">
                          {m.tool_name || 'Tool result'}
                          {m.step_status ? ` - ${m.step_status}` : ''}
                        </div>
                        {m.result ? (
                          <details className="mt-1">
                            <summary className="cursor-pointer text-gray-600 dark:text-gray-300">Show raw result</summary>
                            <pre className="mt-1 overflow-x-auto rounded bg-white dark:bg-gray-950/60 p-2 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify(m.result, null, 2)}
                            </pre>
                          </details>
                        ) : null}
                      </div>
                    ) : null}
                  </>
                )}
              />
            ))
          )}

          {isSending && (
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 py-3">
              <span className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
              <span className="text-sm">Working...</span>
            </div>
          )}
        </div>

        <form
          className="mx-4 mt-2 mb-4 p-3 bg-white dark:bg-[#1b2528] shadow-sm rounded-xl border border-gray-200/80 dark:border-gray-700/80 flex items-center gap-2 flex-shrink-0"
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
        >
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={session?.status === FACTORY_AGENT_STATUS.PLANNING ? 'Planning in progress...' : 'Ask factory agent...'}
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

