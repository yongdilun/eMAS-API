import ActivityTimeline from './ActivityTimeline'
import {
  activityStepsFromResponseDocument,
  humanizeResponseDocumentKey,
  responseDocumentMessage,
  tablePresentationFromResponseRows,
} from './responseDocumentContract.js'
import { TablePresentation } from '../turns/TurnBlocks'

const PREVIEW_LIMIT = 5

function safeText(value) {
  return value == null ? '' : String(value).trim()
}

function rowLabel(row, index) {
  const keys = ['job_id', 'machine_id', 'id', 'record_id', 'name']
  for (const key of keys) {
    if (row?.[key] != null && row[key] !== '') return String(row[key])
  }
  const first = Object.values(row || {}).find((value) => value != null && value !== '')
  return first == null ? `Record ${index + 1}` : String(first)
}

function RowPreview({ rows = [], limit = PREVIEW_LIMIT }) {
  const safeRows = Array.isArray(rows) ? rows : []
  if (!safeRows.length) return null
  const preview = safeRows.slice(0, limit)
  const remaining = Math.max(0, safeRows.length - preview.length)
  return (
    <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-ink-muted">
      {preview.map((row, index) => (
        <span key={`${rowLabel(row, index)}-${index}`} className="rounded-md bg-surface-3 px-2 py-1">
          {rowLabel(row, index)}
        </span>
      ))}
      {remaining > 0 ? (
        <span className="rounded-md bg-surface-3 px-2 py-1">+{remaining} more</span>
      ) : null}
    </div>
  )
}

function CompactCard({ title, children, tone = 'default' }) {
  const toneClass = tone === 'error'
    ? 'border-hairline bg-surface-1'
    : tone === 'warning'
      ? 'border-hairline bg-surface-1'
      : 'border-hairline bg-surface-1'
  return (
    <div className={`mt-3 rounded-md border px-3 py-3 text-sm ${toneClass}`}>
      {title ? <div className="text-sm font-semibold text-ink">{title}</div> : null}
      {children}
    </div>
  )
}

function ExpandableTable({ title, rows, defaultCollapsed = true }) {
  const presentation = tablePresentationFromResponseRows(rows, title)
  if (!presentation) return null
  if (!defaultCollapsed) {
    return <TablePresentation presentation={presentation} />
  }
  return (
    <details className="mt-2 rounded-md border border-hairline bg-surface-2">
      <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-ink-subtle">
        {title} ({rows.length})
      </summary>
      <div className="border-t border-hairline">
        <TablePresentation presentation={presentation} defaultCollapsed={false} />
      </div>
    </details>
  )
}

function ApprovalBlock({
  block,
  pendingApproval,
  showApprovalActions,
  decideApproval,
  isDecidingApproval,
}) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Approval required'}>
      <div className="mt-1 text-sm text-ink">{block.summary || 'Review the proposed change before it is applied.'}</div>
      <RowPreview rows={rows} limit={5} />
      {rows.length > 5 ? (
        <ExpandableTable title="Affected records" rows={rows} defaultCollapsed={block.details_collapsed !== false} />
      ) : null}
      {showApprovalActions ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={isDecidingApproval}
            aria-busy={isDecidingApproval ? 'true' : 'false'}
            onClick={() => decideApproval?.('approve', pendingApproval?.args)}
            className="inline-flex min-w-[6.5rem] items-center justify-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-70"
          >
            {isDecidingApproval ? 'Approving...' : 'Approve'}
          </button>
          <button
            type="button"
            disabled={isDecidingApproval}
            onClick={() => decideApproval?.('reject')}
            className="rounded-md bg-inverse-canvas px-3 py-1.5 text-xs font-semibold text-inverse-ink hover:opacity-90 disabled:opacity-60"
          >
            Reject
          </button>
        </div>
      ) : null}
    </CompactCard>
  )
}

function CompletedStepBlock({ block }) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Completed step'}>
      <div className="mt-1 text-sm text-ink">{block.summary}</div>
      <RowPreview rows={rows} limit={3} />
      {rows.length > 3 ? (
        <ExpandableTable title="Completed records" rows={rows} defaultCollapsed={block.details_collapsed !== false} />
      ) : null}
    </CompactCard>
  )
}

function ResultSummaryBlock({ block }) {
  const steps = Array.isArray(block.steps) ? block.steps : []
  return (
    <CompactCard title={block.title || 'Result summary'}>
      <div className="mt-1 text-sm text-ink">{block.summary}</div>
      {steps.length ? (
        <div className="mt-2 space-y-1 text-xs text-ink-muted">
          {steps.map((step, index) => (
            <div key={`${step.approval_id || step.operation_id || index}`} className="rounded-md bg-surface-2 px-2.5 py-2">
              <span className="font-semibold text-ink-muted">Step {step.step_number || index + 1}</span>
              {step.summary ? <span>: {step.summary}</span> : null}
            </div>
          ))}
        </div>
      ) : null}
    </CompactCard>
  )
}

function MutationResultBlock({ block }) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Mutation result'}>
      <div className="mt-1 text-sm text-ink">{block.summary}</div>
      <RowPreview rows={rows} limit={5} />
      {rows.length > 5 ? <ExpandableTable title="Affected records" rows={rows} /> : null}
    </CompactCard>
  )
}

function RecordPreviewBlock({ block }) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Records'}>
      <RowPreview rows={rows} limit={5} />
      {rows.length > 5 ? <ExpandableTable title={block.title || 'Records'} rows={rows} defaultCollapsed={block.details_collapsed !== false} /> : null}
    </CompactCard>
  )
}

function SourceListBlock({ block }) {
  const sources = Array.isArray(block.sources) ? block.sources : []
  if (!sources.length) return null
  return (
    <CompactCard title={block.title || 'Knowledge sources'}>
      <div className="mt-2 space-y-2 text-xs text-ink-muted">
        {sources.map((source, index) => {
          const title = safeText(source.title || source.doc_id || `Source ${index + 1}`)
          return (
            <div key={`${source.doc_id || title}-${index}`} className="rounded-md bg-surface-2 px-2.5 py-2">
              <div className="font-semibold text-ink">{title}</div>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                {['doc_id', 'machine_id', 'organization'].map((key) => (
                  source[key] ? <span key={key}>{humanizeResponseDocumentKey(key)}: {String(source[key])}</span> : null
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </CompactCard>
  )
}

function DiagnosticBlock({ block }) {
  const technicalDetails = block.technical_details && typeof block.technical_details === 'object'
    ? block.technical_details
    : {}
  return (
    <CompactCard title={block.title || 'Needs attention'} tone={block.severity === 'error' ? 'error' : 'warning'}>
      <div className="mt-1 text-sm text-ink">{block.user_message || block.summary || 'The request could not be completed.'}</div>
      <div className="mt-2 space-y-1 text-xs text-ink-muted">
        {block.cause ? <div><span className="font-semibold text-ink-muted">Cause:</span> {block.cause}</div> : null}
        {block.current_state ? <div><span className="font-semibold text-ink-muted">Current state:</span> {block.current_state}</div> : null}
        {block.next_action ? <div><span className="font-semibold text-ink-muted">Next action:</span> {block.next_action}</div> : null}
      </div>
      {block.impact && Object.keys(block.impact).length ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs font-medium text-ink-subtle">Impact details</summary>
          <div className="mt-2 space-y-1 text-xs text-ink-muted">
            {Object.entries(block.impact).slice(0, 8).map(([key, value]) => (
              <div key={key}>
                <span className="font-semibold text-ink-muted">{humanizeResponseDocumentKey(key)}:</span>{' '}
                {Array.isArray(value) ? value.join(', ') : String(value)}
              </div>
            ))}
          </div>
        </details>
      ) : null}
      <details className="mt-2" open={block.details_collapsed === false}>
        <summary className="cursor-pointer text-xs font-medium text-ink-subtle">Technical details</summary>
        <div className="mt-2 rounded-md bg-surface-2 px-2.5 py-2 text-xs text-ink-muted">
          {Object.keys(technicalDetails).length ? (
            Object.entries(technicalDetails).slice(0, 12).map(([key, value]) => (
              <div key={key} className="break-words">
                <span className="font-semibold">{humanizeResponseDocumentKey(key)}:</span>{' '}
                {Array.isArray(value) ? value.join(', ') : typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}
              </div>
            ))
          ) : (
            <div>No technical details were provided.</div>
          )}
        </div>
      </details>
    </CompactCard>
  )
}

function renderBlock(block, props) {
  if (!block || block.type === 'run_activity' || block.type === 'short_message') return null
  if (block.type === 'approval_required') return <ApprovalBlock key={block.id} block={block} {...props} />
  if (block.type === 'completed_step') return <CompletedStepBlock key={block.id} block={block} />
  if (block.type === 'result_summary') return <ResultSummaryBlock key={block.id} block={block} />
  if (block.type === 'mutation_result') return <MutationResultBlock key={block.id} block={block} />
  if (block.type === 'result_table') return <ExpandableTable key={block.id} title={block.title || 'Affected records'} rows={block.rows} defaultCollapsed />
  if (block.type === 'record_preview') return <RecordPreviewBlock key={block.id} block={block} />
  if (block.type === 'knowledge_answer') return <div key={block.id} className="mt-3 whitespace-pre-wrap break-words text-sm text-ink">{block.answer}</div>
  if (block.type === 'source_list') return <SourceListBlock key={block.id} block={block} />
  if (block.type === 'warning' || block.type === 'diagnostic') return <DiagnosticBlock key={block.id} block={block} />
  return null
}

export default function ResponseDocumentRenderer({
  document,
  pendingApproval,
  showApprovalActions,
  decideApproval,
  isDecidingApproval,
}) {
  if (!document) return null
  const activitySteps = activityStepsFromResponseDocument(document)
  const message = responseDocumentMessage(document)
  const renderedBlocks = (document.blocks || []).map((block) => renderBlock(block, {
    pendingApproval,
    showApprovalActions,
    decideApproval,
    isDecidingApproval,
  })).filter(Boolean)

  return (
    <>
      <ActivityTimeline steps={activitySteps} />
      {message ? <div className="whitespace-pre-wrap break-words text-ink">{message}</div> : null}
      {renderedBlocks}
    </>
  )
}
