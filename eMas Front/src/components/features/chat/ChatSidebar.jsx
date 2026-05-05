const ChatSidebar = ({ conversations = [], activeChatId, onSelectChat, onNewConversation, loading }) => {
 const formatDate = (iso) => {
 if (!iso) return ''
 try {
 const d = new Date(iso)
 const now = new Date()
 const diff = now - d
 if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
 if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' })
 return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
 } catch {
 return ''
 }
 }

 return (
 <aside className="w-52 shrink-0 flex flex-col bg-surface-1 border-r border-hairline p-4 overflow-y-auto">
 <div className="flex flex-col gap-4">
 <button
 type="button"
 onClick={onNewConversation}
 disabled={loading}
 className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-primary text-white text-sm font-semibold hover:bg-primary-hover transition-colors disabled:opacity-60"
 >
 <span className="material-symbols-outlined text-lg">add</span>
 New Conversation
 </button>

 <section>
 <h3 className="text-[11px] font-semibold uppercase tracking-wider text-ink-subtle mb-2">
 Recent Chats
 </h3>
 {loading && conversations.length === 0 ? (
 <div className="px-3 py-4 text-center text-sm text-ink-subtle">
 Loading…
 </div>
 ) : conversations.length === 0 ? (
 <div className="flex flex-col items-center text-center py-6">
 <div className="w-16 h-16 rounded-full bg-surface-2 border border-hairline flex items-center justify-center mb-3">
 <span className="material-symbols-outlined text-3xl text-ink-subtle">
 forum
 </span>
 </div>
 <p className="text-sm text-ink-subtle mb-3">No conversations yet</p>
 <button
 type="button"
 onClick={onNewConversation}
 disabled={loading}
 className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-md hover:bg-primary-hover transition-colors disabled:opacity-60"
 >
 Start your first chat
 </button>
 </div>
 ) : (
 <ul className="space-y-1">
 {conversations.map((c) => (
 <li key={c.id}>
 <button
 type="button"
 onClick={() => onSelectChat(c.id)}
 className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors truncate border ${
 c.id === activeChatId
 ? 'bg-primary/10 text-primary border-primary/30'
 : 'text-ink-muted hover:bg-surface-2 border-transparent hover:border-hairline'
 }`}
 >
 <div className="truncate">{c.title || 'Conversation'}</div>
 {c.updated_at || c.created_at ? (
 <div className="text-[10px] text-ink-subtle mt-0.5">
 {formatDate(c.updated_at || c.created_at)}
 </div>
 ) : null}
 </button>
 </li>
 ))}
 </ul>
 )}
 </section>
 </div>
 </aside>
 )
}

export default ChatSidebar
