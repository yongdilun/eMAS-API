/**
 * Context card with embedded chart (e.g. OEE trend).
 */
export const AiChatContextCard = ({ title, chartData = [] }) => {
 if (!chartData?.length) return null
 const values = chartData.map((d) => d.y ?? d.value ?? 0)
 const min = Math.min(...values)
 const max = Math.max(...values)
 const range = max - min || 1
 const padding = 4
 const w = 280
 const h = 80
 const points = chartData
 .map((d, i) => {
 const x = padding + (i / Math.max(chartData.length - 1, 1)) * (w - padding * 2)
 const y = h - padding - ((d.y ?? d.value ?? 0) - min) / range * (h - padding * 2)
 return `${x},${y}`
 })
 .join(' ')

 return (
 <div className="mt-3 rounded-lg border border-hairline bg-surface-2 p-3 text-xs">
 <div className="font-semibold text-ink mb-2">{title}</div>
 <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" preserveAspectRatio="none">
 <polyline
 points={points}
 fill="none"
 stroke="rgb(96, 165, 250)"
 strokeWidth="1.5"
 strokeLinecap="round"
 strokeLinejoin="round"
 />
 <polyline
 points={chartData.length > 1 ? points : ''}
 fill="none"
 stroke="rgb(248, 113, 113)"
 strokeWidth="1"
 strokeDasharray="4 2"
 strokeLinecap="round"
 strokeLinejoin="round"
 opacity="0.8"
 />
 </svg>
 <div className="flex gap-4 mt-1 text-[10px] text-ink-subtle">
 <span className="flex items-center gap-1">
 <span className="w-2 h-0.5 bg-blue-400 rounded" />
 OEE (%)
 </span>
 </div>
 </div>
 )
}

/**
 * Presentational blocks for AI chat messages: result cards, assist, proposal, and action cards.
 */

const METHOD_STYLES = {
 GET: 'bg-primary/10 text-primary border-primary/25',
 POST: 'bg-primary/10 text-primary border-primary/25',
 PUT: 'bg-surface-3 text-ink-muted border-hairline',
 PATCH: 'bg-surface-3 text-ink-muted border-hairline',
 DELETE: 'bg-surface-3 text-ink border-hairline',
}

export const AiChatActionCard = ({ calls = [], onExecute, executingCallKey }) => {
 if (!calls.length) return null
 return (
 <div className="mt-3 space-y-2">
 {calls.map((call, i) => {
 const method = (call.method || 'GET').toUpperCase()
 const style = METHOD_STYLES[method] || METHOD_STYLES.GET
 const key = `${call.method}-${call.path}-${i}`
 const isExecuting = executingCallKey === key
 const needsApproval = true
 return (
 <div
 key={key}
 className="rounded-lg border border-hairline bg-surface-1 p-3"
 >
 <div className="flex items-start justify-between gap-2">
 <div className="flex-1 min-w-0">
 <span className={`inline-flex px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide border ${style}`}>
 {method}
 </span>
 <p className="mt-1.5 text-sm text-ink">
 {call.purpose || `${method} ${call.path}`}
 </p>
 <p className="mt-1 text-[11px] text-ink-subtle break-all">
 {call.path}
 </p>
 </div>
 <button
 type="button"
 onClick={() => onExecute(call, key)}
 disabled={isExecuting}
 className="shrink-0 px-3 py-1.5 rounded-md text-xs font-semibold bg-primary text-white hover:bg-primary-hover disabled:opacity-60 transition-colors"
 >
 {isExecuting ? (
 <span className="inline-flex items-center gap-1.5">
 <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
 Running…
 </span>
 ) : needsApproval ? 'Approve' : 'Run'}
 </button>
 </div>
 </div>
 )
 })}
 </div>
 )
}

export const AiChatResultCard = ({ card }) => {
 if (card?.kind === 'oee_trend' && card?.chartData) {
 return <AiChatContextCard title={card.title || 'OEE Trend'} chartData={card.chartData} />
 }
 const tone =
 card.tone === 'critical'
 ? 'bg-red-500/10 text-ink-muted '
 : card.tone === 'warning'
 ? 'bg-surface-3 text-ink-muted'
 : card.tone === 'positive'
 ? 'bg-primary/10 text-primary'
 : 'bg-blue-500/10 text-primary'

 return (
 <div className="mt-3 rounded-lg border border-hairline bg-surface-1 p-3.5 text-xs space-y-2">
 <div className="flex items-center justify-between gap-2">
 <div className="font-semibold text-ink">
 {card.title || card.kind || 'Insight'}
 </div>
 <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${tone}`}>
 {card.tone || 'info'}
 </span>
 </div>
 {card.summary && (
 <p className="text-ink-muted text-xs leading-relaxed">{card.summary}</p>
 )}
 {Array.isArray(card.metrics) && card.metrics.length > 0 && (
 <div className="flex flex-wrap gap-2 mt-1">
 {card.metrics.map((m, i) => (
 <div
 key={i}
 className="rounded-md border border-hairline bg-surface-2 px-2 py-1 text-ink"
 >
 <span className="font-semibold">{m.label}: </span>
 <span>{m.value}</span>
 </div>
 ))}
 </div>
 )}
 {Array.isArray(card.bullets) && card.bullets.length > 0 && (
 <ul className="list-disc list-inside text-ink-subtle space-y-0.5">
 {card.bullets.map((b, i) => (
 <li key={i}>{b}</li>
 ))}
 </ul>
 )}
 </div>
 )
}

export const AiChatAssistBlock = ({ msg }) => {
 const data = msg.assist?.data || msg.assist || {}
 const delayRisk = data.delay_risk || {}
 return (
 <div className="mt-3 rounded-lg border border-hairline bg-surface-2 p-3.5 text-xs space-y-1.5">
 <div className="font-semibold text-ink">
 Scheduling assist for job {data.job_id || msg.jobId}
 </div>
 {delayRisk.risk_level && (
 <div className="text-ink">
 Risk level: <span className="font-semibold">{delayRisk.risk_level}</span>{' '}
 (score {delayRisk.risk_score})
 </div>
 )}
 {Array.isArray(data.explanation) && data.explanation.length > 0 && (
 <ul className="list-disc list-inside text-ink-muted space-y-0.5">
 {data.explanation.slice(0, 3).map((l, i) => (
 <li key={i}>{l}</li>
 ))}
 </ul>
 )}
 </div>
 )
}

export const AiChatProposalBlock = ({ msg, onApprove, onApply }) => {
 const proposal = msg.proposal?.data || msg.proposal || {}
 const slots = proposal.proposed_slots || []
 return (
 <div className="mt-3 rounded-lg border border-hairline bg-surface-2 p-3.5 text-xs space-y-2">
 <div className="flex items-center justify-between gap-2">
 <div className="font-semibold text-ink">
 Proposal {proposal.proposal_id || ''} for job {proposal.job_id || msg.jobId}
 </div>
 <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary">
 {proposal.status || 'draft'}
 </span>
 </div>
 {Array.isArray(proposal.summary) && proposal.summary.length > 0 && (
 <ul className="list-disc list-inside text-ink space-y-0.5">
 {proposal.summary.slice(0, 3).map((l, i) => (
 <li key={i}>{l}</li>
 ))}
 </ul>
 )}
 {slots.length > 0 && (
 <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-hairline">
 <table className="w-full text-[11px]">
 <thead className="bg-surface-3 text-ink-muted">
 <tr>
 <th className="px-2 py-1.5 text-left font-medium">Step</th>
 <th className="px-2 py-1.5 text-left font-medium">Machine</th>
 <th className="px-2 py-1.5 text-left font-medium">Start</th>
 <th className="px-2 py-1.5 text-left font-medium">End</th>
 </tr>
 </thead>
 <tbody>
 {slots.slice(0, 20).map((s, i) => (
 <tr key={i} className="border-t border-hairline">
 <td className="px-2 py-1.5">{s.step_name}</td>
 <td className="px-2 py-1.5">{s.machine_name || s.machine_id}</td>
 <td className="px-2 py-1.5">
 {s.scheduled_start ? new Date(s.scheduled_start).toLocaleString() : '—'}
 </td>
 <td className="px-2 py-1.5">
 {s.scheduled_end ? new Date(s.scheduled_end).toLocaleString() : '—'}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}
 <div className="flex gap-2 pt-2">
 <button
 type="button"
 onClick={() => onApprove(proposal)}
 className="px-3 py-1.5 rounded-md bg-inverse-canvas text-inverse-ink text-xs font-semibold hover:opacity-90 transition-opacity"
 >
 Approve proposal
 </button>
 <button
 type="button"
 onClick={() => onApply(proposal)}
 className="px-3 py-1.5 rounded-md bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors"
 >
 Apply to schedule
 </button>
 </div>
 </div>
 )
}
