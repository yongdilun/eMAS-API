const statusCopy = {
  IDLE: {
    tone: 'bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-900/40 dark:border-gray-700 dark:text-gray-300',
    text: 'Session idle. You can start a new task.',
  },
  PLANNING: {
    tone: 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-700/50 dark:text-indigo-300',
    text: 'Planning in progress.',
  },
  WAITING_APPROVAL: {
    tone: 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-700/50 dark:text-amber-300',
    text: 'Waiting for operator approval.',
  },
  EXECUTING: {
    tone: 'bg-sky-50 border-sky-200 text-sky-700 dark:bg-sky-900/20 dark:border-sky-700/50 dark:text-sky-300',
    text: 'Execution in progress.',
  },
  BLOCKED: {
    tone: 'bg-orange-50 border-orange-200 text-orange-700 dark:bg-orange-900/20 dark:border-orange-700/50 dark:text-orange-300',
    text: 'Execution blocked. Review and retry or cancel.',
  },
  FAILED: {
    tone: 'bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-700/50 dark:text-red-300',
    text: 'Session failed. Start a new session or retry from current state.',
  },
  COMPLETED: {
    tone: 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-700/50 dark:text-emerald-300',
    text: 'Session completed successfully.',
  },
}

const SessionStatusBanner = ({ session, onRetry }) => {
  if (!session?.status) return null
  const info = statusCopy[session.status] || statusCopy.IDLE

  return (
    <div className={`mb-3 rounded-xl border px-3 py-2 text-xs ${info.tone}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium">{info.text}</div>
        {(session.status === 'BLOCKED' || session.status === 'FAILED') && (
          <button
            type="button"
            onClick={onRetry}
            className="px-2 py-1 rounded-md text-xs font-semibold bg-white/70 dark:bg-black/30 hover:bg-white dark:hover:bg-black/40"
          >
            Retry
          </button>
        )}
      </div>
      {session.error ? <div className="mt-1 opacity-90">Reason: {session.error}</div> : null}
    </div>
  )
}

export default SessionStatusBanner

