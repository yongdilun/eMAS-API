/* eslint-disable react/prop-types */
import { getReadableAction } from './turnAssembler'

function JsonDetails({ summary, value }) {
  if (value == null) return null
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-gray-600 dark:text-gray-300">{summary}</summary>
      <pre className="mt-2 overflow-x-auto rounded bg-white dark:bg-gray-950/60 p-2 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify(value, null, 2)}
      </pre>
    </details>
  )
}

export function ThinkingBlock({ items = [] }) {
  const rows = Array.isArray(items) ? items : []
  if (!rows.length) return null

  const latest = rows[rows.length - 1]
  const content = latest?.details?.plan_explanation || latest?.content || ''
  const risk = latest?.details?.risk_summary

  return (
    <div className="mt-2 rounded-xl border border-indigo-200/70 dark:border-indigo-800/40 bg-indigo-50/50 dark:bg-indigo-950/15 p-3 text-xs">
      <details>
        <summary className="cursor-pointer font-semibold text-indigo-700 dark:text-indigo-200">
          Thinking (View Plan)
        </summary>
        {content ? (
          <div className="mt-2 whitespace-pre-wrap text-gray-800 dark:text-gray-100">{content}</div>
        ) : (
          <div className="mt-2 text-gray-600 dark:text-gray-300">No plan explanation available.</div>
        )}
        {risk ? (
          <div className="mt-2 rounded-lg bg-indigo-100/60 dark:bg-indigo-900/25 px-2.5 py-2 text-indigo-800 dark:text-indigo-200">
            Risk summary: {risk}
          </div>
        ) : null}
        <JsonDetails summary="Show debug payload" value={latest?.details} />
      </details>
    </div>
  )
}

export function ToolBlocks({ tools = [] }) {
  const rows = Array.isArray(tools) ? tools : []
  if (!rows.length) return null

  return (
    <div className="mt-2 space-y-2">
      {rows.map((t) => {
        const label = `${getReadableAction(t.tool_name)}`
        const status = (t.status || 'DONE').toString()
        const title = label
        const upper = String(status).toUpperCase()
        const pill = upper === 'DONE'
          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
          : upper === 'FAILED'
            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
            : upper === 'IN_PROGRESS'
              ? 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300'
              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'

        return (
          <div key={t.id} className="rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-gray-50 dark:bg-gray-900/40 p-3 text-xs">
            <details>
              <summary className="cursor-pointer flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-gray-800 dark:text-gray-100">
                  {title}
                </span>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${pill}`}>
                  {status}
                </span>
              </summary>
              {t.tool_name ? (
                <div className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
                  Tool: {t.tool_name}
                </div>
              ) : null}
              {t.content ? (
                <div className="mt-2 whitespace-pre-wrap text-gray-700 dark:text-gray-200">{t.content}</div>
              ) : null}
              <JsonDetails summary="Show args/result" value={t.details} />
            </details>
          </div>
        )
      })}
    </div>
  )
}

export function ApprovalBlocks({ approvals = [] }) {
  const rows = Array.isArray(approvals) ? approvals : []
  if (!rows.length) return null

  return (
    <div className="mt-2 space-y-2">
      {rows.map((a) => {
        const title = a.event_type === 'approval_required' ? 'Approval required' : 'Approval decided'
        const tone = a.event_type === 'approval_required'
          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
          : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
        return (
          <div key={a.id} className="rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-gray-50 dark:bg-gray-900/40 p-3 text-xs">
            <details>
              <summary className="cursor-pointer flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-gray-800 dark:text-gray-100">
                  {title}
                </span>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${tone}`}>
                  {a.status || a.event_type}
                </span>
              </summary>
              {a.tool_name ? (
                <div className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
                  Tool: {a.tool_name}
                </div>
              ) : null}
              {a.content ? (
                <div className="mt-2 whitespace-pre-wrap text-gray-700 dark:text-gray-200">{a.content}</div>
              ) : null}
              <JsonDetails summary="Show details" value={a.details} />
            </details>
          </div>
        )
      })}
    </div>
  )
}

export function LegacyBlocks({ blocks = [] }) {
  const rows = Array.isArray(blocks) ? blocks : []
  if (!rows.length) return null

  return (
    <div className="mt-2 space-y-2">
      {rows.map((b, idx) => {
        if (b.type === 'thinking') {
          return (
            <div key={`${b.type}-${idx}`} className="rounded-xl border border-indigo-200/70 dark:border-indigo-800/40 bg-indigo-50/50 dark:bg-indigo-950/15 p-3 text-xs">
              <details>
                <summary className="cursor-pointer font-semibold text-indigo-700 dark:text-indigo-200">
                  Thinking (View)
                </summary>
                <pre className="mt-2 overflow-x-auto rounded bg-white dark:bg-gray-950/60 p-2 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify(b.payload, null, 2)}
                </pre>
              </details>
            </div>
          )
        }

        if (b.type === 'tool_call') {
          const action = getReadableAction(b.action || b.tool_name)
          return (
            <div key={`${b.type}-${idx}`} className="rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-gray-50 dark:bg-gray-900/40 p-3 text-xs">
              <details>
                <summary className="cursor-pointer flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate text-gray-800 dark:text-gray-100">
                    {action}
                  </span>
                  <span className="shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                    {b.status || 'SUGGESTED'}
                  </span>
                </summary>
                {(b.title || b.tool_name) ? (
                  <div className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
                    Tool: {b.title || b.tool_name}
                  </div>
                ) : null}
                <pre className="mt-2 overflow-x-auto rounded bg-white dark:bg-gray-950/60 p-2 text-[11px] text-gray-700 dark:text-gray-200">
{JSON.stringify(b.payload, null, 2)}
                </pre>
              </details>
            </div>
          )
        }

        return null
      })}
    </div>
  )
}
