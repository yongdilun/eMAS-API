import { useEffect, useMemo, useState } from 'react'
import { factoryAgentApi } from '../../../../services/factoryAgentApi'

const levelStyles = {
  NONE: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  LOW: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  HIGH: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

const ApprovalCard = ({ approval, reason, onReasonChange, onApprove, onReject, deciding }) => {
  if (!approval) return null

  const level = approval.side_effect_level || 'HIGH'
  const badgeClass = levelStyles[level] || levelStyles.HIGH
  const [tools, setTools] = useState([])
  const [argsText, setArgsText] = useState(() => JSON.stringify(approval.args || {}, null, 2))

  useEffect(() => {
    setArgsText(JSON.stringify(approval.args || {}, null, 2))
  }, [approval?.approval_id])

  useEffect(() => {
    let cancelled = false
    const loadTools = async () => {
      try {
        const rows = await factoryAgentApi.listTools({ max_tools: 200 })
        if (!cancelled) setTools(Array.isArray(rows) ? rows : [])
      } catch {
        if (!cancelled) setTools([])
      }
    }
    loadTools()
    return () => {
      cancelled = true
    }
  }, [])

  const tool = useMemo(() => (tools || []).find((t) => t?.name === approval.tool_name) || null, [tools, approval?.tool_name])
  const required = useMemo(() => {
    const req = tool?.input_schema?.required
    return Array.isArray(req) ? req : []
  }, [tool?.input_schema?.required])

  const parsedArgs = useMemo(() => {
    const out = { value: null, error: null }
    try {
      const parsed = JSON.parse(argsText || '{}')
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        out.value = parsed
        return out
      }
      out.error = 'Args must be a JSON object.'
      return out
    } catch (e) {
      out.error = e?.message || 'Invalid JSON'
      return out
    }
  }, [argsText])

  return (
    <div className="rounded-xl border border-amber-200/80 dark:border-amber-800/50 bg-amber-50/70 dark:bg-amber-950/20 p-4 mt-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-200">Approval required</h3>
        <span className={`text-[10px] px-2 py-1 rounded-full font-semibold ${badgeClass}`}>
          {level}
        </span>
      </div>

      <div className="mt-2 text-xs text-gray-700 dark:text-gray-300">
        <div><span className="font-semibold">Tool:</span> {approval.tool_name}</div>
        <div className="mt-1"><span className="font-semibold">Risk:</span> {approval.risk_summary || 'No risk summary provided.'}</div>
      </div>

      {required.length > 0 ? (
        <div className="mt-2 text-[11px] text-gray-700 dark:text-gray-300">
          <span className="font-semibold">Required fields:</span>{' '}
          {required.map((k) => (
            <span
              key={k}
              className={`inline-flex items-center px-1.5 py-0.5 rounded mr-1 mt-1 ${
                parsedArgs.value && parsedArgs.value[k] != null && parsedArgs.value[k] !== ''
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200'
                  : 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-200'
              }`}
            >
              {k}
            </span>
          ))}
        </div>
      ) : null}

      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-gray-600 dark:text-gray-400">Edit args (JSON)</summary>
        {parsedArgs.error ? (
          <div className="mt-2 text-[11px] text-red-700 dark:text-red-300">{parsedArgs.error}</div>
        ) : null}
        <textarea
          value={argsText}
          onChange={(e) => setArgsText(e.target.value)}
          className="mt-2 w-full rounded bg-gray-100 dark:bg-gray-900/60 p-2 text-[11px] text-gray-800 dark:text-gray-200 font-mono overflow-x-auto"
          rows={8}
        />
        <pre className="mt-2 text-[11px] p-2 rounded bg-gray-100 dark:bg-gray-900/60 text-gray-800 dark:text-gray-200 overflow-x-auto">
{JSON.stringify(approval.args || {}, null, 2)}
        </pre>
      </details>

      <textarea
        value={reason}
        onChange={(e) => onReasonChange(e.target.value)}
        placeholder="Optional rejection reason"
        className="w-full mt-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 px-3 py-2 text-xs text-gray-900 dark:text-white"
        rows={2}
      />

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          disabled={deciding || !!parsedArgs.error || !parsedArgs.value}
          onClick={() => onApprove(parsedArgs.value || undefined)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          Approve
        </button>
        <button
          type="button"
          disabled={deciding}
          onClick={onReject}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
        >
          Reject
        </button>
      </div>
    </div>
  )
}

export default ApprovalCard
