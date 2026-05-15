import { friendlySessionStatus } from './activityTimelineUtils'

const FactoryAgentSessionSidebar = ({
  collapsed,
  onCollapsedChange,
  sessions,
  activeSessionId,
  editingSessionId,
  editingName,
  onEditingNameChange,
  onStartNewSession,
  onSwitchSession,
  onStartEditing,
  onStopEditing,
  onRenameSession,
  onDeleteSession,
}) => (
  <aside
    className={`${collapsed ? 'w-14' : 'w-72'} border-r border-hairline bg-surface-1 transition-all duration-200 flex flex-col`}
  >
    <div className="px-2.5 py-2 border-b border-hairline flex items-center gap-2">
      {!collapsed ? (
        <>
          <button
            type="button"
            onClick={onStartNewSession}
            className="flex-1 px-2.5 py-2 rounded-md text-xs font-semibold bg-primary text-white hover:bg-primary-hover"
          >
            New Session
          </button>
          <button
            type="button"
            onClick={() => onCollapsedChange(true)}
            className="p-2 rounded-md hover:bg-surface-2 text-ink-subtle"
            aria-label="Collapse sessions"
          >
            <span className="material-symbols-outlined text-lg">left_panel_close</span>
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={() => onCollapsedChange(false)}
          className="w-full p-2 rounded-md hover:bg-surface-2 text-ink-subtle"
          aria-label="Expand sessions"
        >
          <span className="material-symbols-outlined text-lg">left_panel_open</span>
        </button>
      )}
    </div>

    {!collapsed ? (
      <div className="overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 ? (
          <div className="px-2 py-3 text-xs text-ink-subtle">
            No sessions yet.
          </div>
        ) : (
          sessions.map((item) => {
            const isActive = item.session_id === activeSessionId
            const isEditing = editingSessionId === item.session_id
            return (
              <div
                key={item.session_id}
                className={`group rounded-lg border transition-colors ${isActive
                  ? 'border-primary/50 bg-primary/[0.14] shadow-[inset_4px_0_0_0_#5e6ad2] ring-1 ring-inset ring-primary/20'
                  : 'border-transparent bg-transparent hover:border-hairline hover:bg-surface-2'
                  }`}
              >
                <button
                  type="button"
                  onClick={() => onSwitchSession(item.session_id)}
                  className="w-full text-left px-2.5 py-2"
                >
                  {isEditing ? (
                    <input
                      autoFocus
                      value={editingName}
                      onChange={(e) => onEditingNameChange(e.target.value)}
                      onBlur={() => {
                        onRenameSession(item.session_id, editingName)
                        onStopEditing()
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          onRenameSession(item.session_id, editingName)
                          onStopEditing()
                        }
                        if (e.key === 'Escape') {
                          onStopEditing()
                        }
                      }}
                      className="w-full rounded-md border border-hairline bg-surface-2 px-2 py-1 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
                    />
                  ) : (
                    <div className="flex items-start gap-2">
                      <div className="min-w-0 flex-1">
                        <div className={`truncate text-sm text-ink ${isActive ? 'font-semibold' : 'font-medium'}`}>
                          {item.name}
                        </div>
                        <div className="mt-0.5 text-[11px] uppercase tracking-wide text-ink-subtle">
                          {friendlySessionStatus(item.status)}
                        </div>
                      </div>
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          onStartEditing(item)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            e.stopPropagation()
                            onStartEditing(item)
                          }
                        }}
                        className="material-symbols-outlined text-base text-ink-subtle opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
                      >
                        edit
                      </span>
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          onDeleteSession(item)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            e.stopPropagation()
                            onDeleteSession(item)
                          }
                        }}
                        className="material-symbols-outlined text-base text-ink-subtle opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
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
)

export default FactoryAgentSessionSidebar
