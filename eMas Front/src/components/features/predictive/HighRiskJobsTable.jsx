// Fetches from GET /predictive/high-risk-jobs
// Expected: [{ job_id, machine_id|machine_name, issue|predicted_issue, risk_level }]
// Falls back to demo data when endpoint is unavailable (endpoint not yet implemented)
import { useState, useEffect } from 'react'
import { predictiveApi, toList } from '../../../services/api'
import logger from '../../../services/logger'

const DEMO = [
 { job_id: 'JOB-2403', machine_name: 'Coating Station 01', issue: 'Overdue Maintenance', risk_level: 'High' },
 { job_id: 'JOB-2406', machine_name: 'CNC Mill 02', issue: 'High Load Duration', risk_level: 'Medium' },
 { job_id: 'JOB-2401', machine_name: 'CNC Mill 01', issue: 'Coolant Pressure Drop', risk_level: 'Low' },
]

const RISK_STYLE = {
  High: 'bg-primary/10 text-primary',
  Medium: 'bg-surface-2 text-ink-muted',
  Low: 'bg-semantic-success/10 text-semantic-success',
}

const HighRiskJobsTable = () => {
 const [jobs, setJobs] = useState(DEMO)
 const [loading, setLoading] = useState(true)

 useEffect(() => {
 predictiveApi.highRiskJobs()
 .then(data => {
 const rows = toList(data)
 if (rows.length > 0) setJobs(rows)
 })
 .catch((err) => logger.debug('High-risk jobs API unavailable; using demo data', { message: err?.message }))
 .finally(() => setLoading(false))
 }, [])

 const s = (v, fb = '—') => { const x = v; return (x !== undefined && x !== null) ? String(typeof x === 'object' ? (x.value ?? x.label ?? x.name ?? fb) : x) : fb }
 const normalise = (j) => ({
 id: s(j.job_id ?? j.id),
 machine: s(j.machine_name ?? j.machine_id ?? j.machine),
 issue: s(j.issue ?? j.predicted_issue ?? j.reason),
 riskLevel: s(j.risk_level ?? j.riskLevel, 'Low'),
 })

  return (
    <div className="rounded-lg border border-hairline bg-surface-1 overflow-hidden">
      <div className="flex items-center justify-between border-b border-hairline px-4 py-3 bg-surface-2">
        <h2 className="text-lg font-semibold text-ink">High-Risk Jobs</h2>
        {loading && <span className="w-4 h-4 border-2 border-hairline border-t-primary rounded-full animate-spin" />}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-ink-muted">
          <thead className="text-xs uppercase text-ink-subtle bg-surface-1 border-b border-hairline">
            <tr>
              {['Job ID', 'Machine', 'Predicted Issue', 'Risk Level'].map(h => (
                <th key={h} className="px-5 py-3 font-semibold tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => {
              const r = normalise(job)
              return (
                <tr key={r.id} className="border-b border-hairline last:border-b-0 hover:bg-surface-2 transition-colors">
                  <td className="px-5 py-3 font-semibold text-ink whitespace-nowrap">{r.id}</td>
                  <td className="px-5 py-3 whitespace-nowrap text-ink-muted">{r.machine}</td>
                  <td className="px-5 py-3 text-ink-subtle">{r.issue}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-[11px] font-medium ${RISK_STYLE[r.riskLevel] ?? RISK_STYLE.Low}`}>
                      {r.riskLevel}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default HighRiskJobsTable
