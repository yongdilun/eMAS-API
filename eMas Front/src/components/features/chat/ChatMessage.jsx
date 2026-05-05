/**
 * Chat message with avatar, timestamp, content, and optional embedded blocks.
 */
const ChatMessage = ({
 message,
 isUser = false,
 timestamp,
 renderBlocks,
 messageAfterBlocks = false,
 animateIn = true,
}) => {
 const hasMessage = message != null && String(message).trim() !== ''
 const bubbleAnim = (!isUser && animateIn) ? 'emas-chat-enter' : ''
 return (
 <div className={`mb-4 flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
 <div
 className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-hairline ${
 isUser
 ? 'bg-primary/10 text-primary'
 : 'bg-surface-2 text-ink-subtle'
 }`}
 >
 <span
 className="material-symbols-outlined text-lg"
 style={!isUser ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" } : {}}
 >
 {isUser ? 'person' : 'smart_toy'}
 </span>
 </div>
 <div
 className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}
 >
 <div className="flex items-center gap-2 mb-1">
 <span className="text-xs font-medium text-ink-subtle">
 {isUser ? 'You' : 'eMAS AI'}
 </span>
 {timestamp && (
 <span className="text-[10px] text-gray-400 dark:text-ink-subtle">
 {timestamp}
 </span>
 )}
 </div>
 <div
 className={`rounded-lg px-4 py-2.5 text-sm leading-relaxed ${bubbleAnim} ${
 isUser
 ? 'rounded-br-sm bg-primary text-white'
 : 'rounded-bl-sm border border-hairline bg-surface-1 text-ink'
 }`}
 >
 {messageAfterBlocks ? renderBlocks?.() : null}
 {hasMessage ? <div className="whitespace-pre-wrap break-words">{message}</div> : null}
 {!messageAfterBlocks ? renderBlocks?.() : null}
 </div>
 </div>
 </div>
 )
}

export default ChatMessage
