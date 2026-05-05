const statusTone = {
 IDLE: 'text-ink-muted',
 PLANNING: 'text-ink-muted',
 WAITING_APPROVAL: 'text-ink-muted',
 EXECUTING: 'text-primary',
 BLOCKED: 'text-ink-muted',
 FAILED: 'text-ink',
 COMPLETED: 'text-primary',
}

const ExecutionTracker = ({ session, lastSyncedAt, isPollingSession, isPollingApprovals }) => {
 if (!session) return null
 const tone = statusTone[session.status] || statusTone.IDLE

 return (
 <div className="mb-3 rounded-lg border border-hairline bg-surface-1 p-3">
 <div className="flex items-center justify-between">
 <span className="text-xs font-semibold text-ink-subtle">Session status</span>
 <span className={`text-xs font-semibold ${tone}`}>{session.status}</span>
 </div>
 <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-ink-muted">
 <div>Step index: {session.current_step_index ?? 0}</div>
 <div>Plan version: {session.plan_version ?? 0}</div>
 <div>Steps run: {session.step_count ?? 0}</div>
 <div>Replans: {session.replan_count ?? 0}</div>
 </div>
 {session.pending_user_message ? (
 <div className="mt-2 text-xs text-ink-muted">
 Pending operator message queued.
 </div>
 ) : null}
 {session.error ? (
 <div className="mt-2 text-xs text-ink-muted">Error: {session.error}</div>
 ) : null}
 <div className="mt-2 flex items-center justify-between text-[10px] text-ink-subtle">
 <span>Session poll: {isPollingSession ? 'on' : 'off'}</span>
 <span>Approval poll: {isPollingApprovals ? 'on' : 'off'}</span>
 <span>{lastSyncedAt ? `Synced ${new Date(lastSyncedAt).toLocaleTimeString()}` : 'Not synced yet'}</span>
 </div>
 </div>
 )
}

export default ExecutionTracker
