const Modal = ({ isOpen, onClose, title, children, size = 'default', zIndex }) => {
 if (!isOpen) return null

 const isFullScreen = size === 'fullscreen'
 const baseZ = zIndex ?? 50
 const contentZ = isFullScreen ? baseZ + 1 : baseZ
 const contentClass = isFullScreen
 ? 'fixed inset-4 sm:inset-6 md:inset-8 bg-surface-1 rounded-xl -none border border-hairline flex flex-col overflow-hidden'
 : 'bg-surface-1 rounded-xl -none border border-hairline max-w-2xl w-full mx-4 flex flex-col max-h-[90vh] overflow-hidden'

 return (
 <div
 className="fixed inset-0 bg-black/50 backdrop-blur-sm dark:bg-black/55 flex items-center justify-center p-0"
 style={{ zIndex: baseZ }}
 onClick={(e) => e.target === e.currentTarget && onClose?.()}
 >
 <div className={contentClass} style={{ zIndex: contentZ }} onClick={(e) => e.stopPropagation()}>
 <div className="flex items-center justify-between p-lg border-b border-hairline shrink-0">
 <h2 className="text-card-title text-ink">{title}</h2>
 <button
 onClick={onClose}
 className="p-2 rounded-md text-ink-muted hover:text-ink hover:bg-surface-2 transition-colors"
 aria-label="Close"
 >
 <span className="material-symbols-outlined">close</span>
 </button>
 </div>
 <div className={`flex-1 min-h-0 ${isFullScreen ? 'flex flex-col overflow-hidden p-4 sm:p-6' : 'overflow-auto p-6'}`}>{children}</div>
 </div>
 </div>
 )
}

export default Modal


