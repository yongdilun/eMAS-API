import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAiChat } from './useAiChat'
import { AiChatResultCard, AiChatAssistBlock, AiChatProposalBlock, AiChatActionCard } from './AiChatBlocks'
import ChatSidebar from './ChatSidebar'
import ChatMessage from './ChatMessage'
import { mergeLegacyAssistantTurnContent } from './turns/turnAssembler'
import { LegacyBlocks } from './turns/TurnBlocks'

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const AiChatPanel = ({ onClose, onHeaderMouseDown }) => {
  const chatRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const {
    conversations,
    activeChatId,
    messages,
    turns,
    activeTitle,
    input,
    setInput,
    isSending,
    loading,
    error,
    executingCallKey,
    handleSend,
    handleExecuteSuggestedCall,
    handleApproveProposal,
    handleApplyProposal,
    handleSelectChat,
    handleNewConversation,
  } = useAiChat()

  useEffect(() => {
    if (!chatRef.current) return
    if (!shouldAutoScrollRef.current) return
    chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [turns, messages, isSending])

  const handleChatScroll = () => {
    if (!chatRef.current) return
    const el = chatRef.current
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    shouldAutoScrollRef.current = distanceToBottom < 120
  }

  useEffect(() => {
    shouldAutoScrollRef.current = true
  }, [activeChatId])

  return (
    <div className="flex h-full">
      <ChatSidebar
        conversations={conversations}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewConversation={handleNewConversation}
        loading={loading}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header - title area is draggable */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200/80 dark:border-gray-700/80 bg-white dark:bg-[#111618]">
          <div
            className="flex items-center gap-3 cursor-move select-none flex-1 min-w-0"
            onMouseDown={onHeaderMouseDown}
            data-drag-handle
            role="presentation"
          >
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {activeTitle}
            </h2>
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Active
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Link
              to="/settings"
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
              aria-label="Settings"
            >
              <span className="material-symbols-outlined">settings</span>
            </Link>
            <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-[#283539] flex items-center justify-center ml-1">
              <span className="material-symbols-outlined text-gray-500 dark:text-gray-400 text-lg">
                person
              </span>
            </div>
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

        {/* Error banner */}
        {error && (
          <div className="px-4 py-2 bg-amber-50/80 dark:bg-amber-900/15 border-b border-amber-200/60 dark:border-amber-800/40 text-sm text-amber-700 dark:text-amber-400">
            {error}
          </div>
        )}

        {/* Chat history */}
        <div
          ref={chatRef}
          onScroll={handleChatScroll}
          className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50 dark:bg-gray-900/60"
        >
          {loading && messages.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-400 text-sm">
              Loading conversation…
            </div>
          ) : (turns?.length || 0) === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center px-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-primary">smart_toy</span>
              </div>
              <p className="text-gray-700 dark:text-gray-300 text-sm font-medium">
                How can I help with smart factory operations?
              </p>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-1.5">
                Ask about jobs, scheduling, or production status.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-4">
                {['Status of jobs', 'Reschedule JOB-SEED-001', 'Delay risk for today'].map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            (turns || []).map((turn) => {
              const user = turn.user
              const assistants = Array.isArray(turn.assistants) ? turn.assistants : []
              const primary = assistants[0] || null
              const merged = mergeLegacyAssistantTurnContent(turn)

              const resultCards = assistants.flatMap((a) => (Array.isArray(a?.resultCards) ? a.resultCards : []))
              const assistMsg = assistants.find((a) => a?.kind === 'assist') || null
              const proposalMsg = assistants.find((a) => a?.kind === 'proposal') || null
              const approvalCalls = (primary && Array.isArray(primary.approval_calls)) ? primary.approval_calls : []

              return (
                <div key={turn.id}>
                  {user?.content ? (
                    <ChatMessage message={user.content} isUser timestamp={user.timestamp} />
                  ) : null}

                  <ChatMessage
                    message={merged.content}
                    isUser={false}
                    timestamp={primary?.timestamp}
                    renderBlocks={() => (
                      <>
                        <LegacyBlocks blocks={merged.blocks} />

                        {primary?.ambiguous && Array.isArray(primary?.clarifications) && primary.clarifications.length > 0 && (
                          <div className="mt-2 text-[11px] text-amber-700 dark:text-amber-300">
                            I need a bit more detail:
                            <ul className="list-disc list-inside">
                              {primary.clarifications.map((c, i) => (
                                <li key={i}>{c}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {resultCards.map((c, i) => (
                          <AiChatResultCard key={i} card={c} />
                        ))}

                        {assistMsg ? <AiChatAssistBlock msg={assistMsg} /> : null}
                        {proposalMsg ? (
                          <AiChatProposalBlock msg={proposalMsg} onApprove={handleApproveProposal} onApply={handleApplyProposal} />
                        ) : null}

                        {!primary?.ambiguous && approvalCalls.length > 0 ? (
                          <AiChatActionCard calls={approvalCalls} onExecute={handleExecuteSuggestedCall} executingCallKey={executingCallKey} />
                        ) : null}
                      </>
                    )}
                  />
                </div>
              )
            })
          )}
          {isSending && (
            <ChatMessage
              message=""
              isUser={false}
              timestamp={nowTime()}
              renderBlocks={() => (
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <span className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                  <span className="text-sm">Thinking...</span>
                </div>
              )}
            />
          )}
        </div>

        {/* Input area */}
        <form
          className="mx-4 mt-2 mb-4 p-3 bg-white dark:bg-[#1b2528] shadow-sm rounded-xl border border-gray-200/80 dark:border-gray-700/80 flex items-center gap-2 flex-shrink-0"
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
        >
          <div className="flex-1 flex items-center gap-2">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about jobs, delays, or scheduling…"
              className="flex-1 resize-none rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
            />
          </div>
          <button
            type="submit"
            disabled={isSending || !input.trim()}
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

export default AiChatPanel
