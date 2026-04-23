const statusTone = {
  IDLE: 'text-gray-700 dark:text-gray-300',
  PLANNING: 'text-indigo-700 dark:text-indigo-300',
  WAITING_APPROVAL: 'text-amber-700 dark:text-amber-300',
  EXECUTING: 'text-sky-700 dark:text-sky-300',
  BLOCKED: 'text-orange-700 dark:text-orange-300',
  FAILED: 'text-red-700 dark:text-red-300',
  COMPLETED: 'text-emerald-700 dark:text-emerald-300',
}

const ExecutionTracker = ({ session, lastSyncedAt, isPollingSession, isPollingApprovals }) => {
  if (!session) return null
  const tone = statusTone[session.status] || statusTone.IDLE

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 p-3 mb-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">Session status</span>
        <span className={`text-xs font-semibold ${tone}`}>{session.status}</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-700 dark:text-gray-300">
        <div>Step index: {session.current_step_index ?? 0}</div>
        <div>Plan version: {session.plan_version ?? 0}</div>
        <div>Steps run: {session.step_count ?? 0}</div>
        <div>Replans: {session.replan_count ?? 0}</div>
      </div>
      {session.pending_user_message ? (
        <div className="mt-2 text-xs text-indigo-700 dark:text-indigo-300">
          Pending operator message queued.
        </div>
      ) : null}
      {session.error ? (
        <div className="mt-2 text-xs text-red-700 dark:text-red-300">Error: {session.error}</div>
      ) : null}
      <div className="mt-2 flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400">
        <span>Session poll: {isPollingSession ? 'on' : 'off'}</span>
        <span>Approval poll: {isPollingApprovals ? 'on' : 'off'}</span>
        <span>{lastSyncedAt ? `Synced ${new Date(lastSyncedAt).toLocaleTimeString()}` : 'Not synced yet'}</span>
      </div>
    </div>
  )
}

export default ExecutionTracker
