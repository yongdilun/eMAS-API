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
 <div className="flex items-center justify-between px-4 py-3 border-b border-hairline bg-surface-1">
 <div
 className="flex items-center gap-3 cursor-move select-none flex-1 min-w-0"
 onMouseDown={onHeaderMouseDown}
 data-drag-handle
 role="presentation"
 >
 <h2 className="text-lg font-semibold text-ink truncate">
 {activeTitle}
 </h2>
 <span className="flex items-center gap-1.5 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-ink-subtle">
 <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
 Active
 </span>
 </div>
 <div className="flex items-center gap-1">
 <Link
 to="/settings"
 className="p-2 rounded-md hover:bg-surface-2 text-ink-subtle"
 aria-label="Settings"
 >
 <span className="material-symbols-outlined">settings</span>
 </Link>
 <div className="ml-1 flex h-8 w-8 items-center justify-center rounded-full border border-hairline bg-surface-2">
 <span className="material-symbols-outlined text-ink-subtle text-lg">
 person
 </span>
 </div>
 {onClose && (
 <button
 type="button"
 onClick={onClose}
 className="p-2 rounded-md hover:bg-surface-2 text-ink-subtle"
 aria-label="Close"
 >
 <span className="material-symbols-outlined">close</span>
 </button>
 )}
 </div>
 </div>

 {/* Error banner */}
 {error && (
 <div className="border-b border-hairline bg-surface-2 px-4 py-2 text-sm text-ink-muted">
 {error}
 </div>
 )}

 {/* Chat history */}
 <div
 ref={chatRef}
 onScroll={handleChatScroll}
 className="flex-1 overflow-y-auto bg-canvas px-4 py-4"
 >
 {loading && messages.length === 0 ? (
 <div className="flex items-center justify-center h-32 text-ink-subtle text-sm">
 Loading conversation…
 </div>
 ) : (turns?.length || 0) === 0 ? (
 <div className="flex flex-col items-center justify-center min-h-[200px] text-center px-4">
 <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
 <span className="material-symbols-outlined text-3xl text-primary">smart_toy</span>
 </div>
 <p className="text-ink-muted text-sm font-medium">
 How can I help with smart factory operations?
 </p>
 <p className="text-ink-subtle text-xs mt-1.5">
 Ask about jobs, scheduling, or production status.
 </p>
 <div className="flex flex-wrap justify-center gap-2 mt-4">
 {['Status of jobs', 'Reschedule JOB-SEED-001', 'Delay risk for today'].map((prompt) => (
 <button
 key={prompt}
 type="button"
 onClick={() => handleSend(prompt)}
 className="rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-xs font-medium text-ink-muted transition-colors hover:bg-surface-2"
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
 sources={merged.sources}
 safetyContent={merged.safetyContent}
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
 <div className="flex items-center gap-2 text-ink-subtle">
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
 className="mx-4 mb-4 mt-2 flex flex-shrink-0 items-center gap-2 rounded-lg border border-hairline bg-surface-1 p-2.5"
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
 className="flex-1 resize-none rounded-md border border-hairline bg-surface-2 px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink-tertiary focus:border-primary focus:ring-2 focus:ring-primary/30"
 />
 </div>
 <button
 type="submit"
 disabled={isSending || !input.trim()}
 className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
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
