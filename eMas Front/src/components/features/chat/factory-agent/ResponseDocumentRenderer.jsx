import { useMemo, useState } from 'react'
import ActivityTimeline from './ActivityTimeline'
import {
  activityStepsFromResponseDocument,
  humanizeResponseDocumentKey,
  responseDocumentMessage,
  tablePresentationFromResponseRows,
} from './responseDocumentContract.js'
import { TablePresentation } from '../turns/TurnBlocks'

const PREVIEW_LIMIT = 5
const TECHNICAL_REDACTION_RE = /\b(api[_-]?key|authorization|bearer|password|secret|token)\b\s*[:=]?\s*[^\s,;]+/gi
const SAFETY_ADMONITION_RE = /(?:^|\n)[ \t]*:::\s*safety\b[\s\S]*?(?:\n[ \t]*:::[ \t]*(?=\n|$)|$)/gi
const FOOTNOTE_DEFINITION_RE = /^[ \t]*\[\^[^\]\n]+\]:[^\n]*(?:\n[ \t]+[^\n]*)*/gm
const FOOTNOTE_MARKER_RE = /\[\^[^\]\n]+\]/g

function safeText(value) {
  if (value == null) return ''
  return String(value)
    .replace(SAFETY_ADMONITION_RE, '\n')
    .replace(/^[ \t]*:::\s*safety\b[ \t]*$/gim, '')
    .replace(/^[ \t]*:::[ \t]*$/gim, '')
    .replace(FOOTNOTE_DEFINITION_RE, '')
    .replace(FOOTNOTE_MARKER_RE, '')
    .replace(/\s+([,.;:!?])/g, '$1')
    .trim()
}

function rowLabel(row, index) {
  const keys = ['display_id', 'display_name', 'record_id', 'job_id', 'machine_id', 'id', 'name']
  for (const key of keys) {
    if (row?.[key] != null && row[key] !== '') return String(row[key])
  }
  const first = Object.values(row || {}).find((value) => value != null && value !== '')
  return first == null ? `Record ${index + 1}` : String(first)
}

function rowRecordId(row, index) {
  return rowLabel(row, index)
}

function businessChangeLabel(value, fallback = 'Business change') {
  return safeText(value) || fallback
}

function businessChangeCount(group) {
  const explicit = Number(group?.record_count)
  if (Number.isFinite(explicit)) return explicit
  return Array.isArray(group?.rows) ? group.rows.length : 0
}

function businessChangeSummary(group, fallback) {
  const label = businessChangeLabel(group?.business_change, fallback)
  const count = businessChangeCount(group)
  const entity = safeText(group?.entity_type) || 'record'
  const singular = entity.endsWith('s') ? entity.slice(0, -1) || entity : entity
  return safeText(group?.summary) || `${label}: ${count} ${count === 1 ? singular : `${singular}s`}`
}

function hasSupportedMutationContract(block) {
  if (safeText(block?.contract) === 'business_change_v1') return true
  const groups = Array.isArray(block?.groups) ? block.groups : []
  return groups.some((group) => ['business_change_v1', 'entity_agnostic_no_matching_records_v1'].includes(safeText(group?.contract)))
}

function fieldChangeSummary(changes) {
  if (!Array.isArray(changes) || !changes.length) return ''
  return changes
    .map((change) => {
      const label = safeText(change?.label || change?.field) || 'Value'
      const before = safeText(change?.from)
      const after = safeText(change?.to)
      if (before && after) return `${label}: ${before} -> ${after}`
      if (after) return `${label}: ${after}`
      if (before) return `${label}: ${before}`
      return label
    })
    .filter(Boolean)
    .join('; ')
}

function RowPreview({ rows = [], limit = PREVIEW_LIMIT }) {
  const safeRows = Array.isArray(rows) ? rows : []
  if (!safeRows.length) return null
  const preview = safeRows.slice(0, limit)
  const remaining = Math.max(0, safeRows.length - preview.length)
  return (
    <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-ink-muted" data-affected-record-preview="">
      {preview.map((row, index) => (
        <span
          key={`${rowLabel(row, index)}-${index}`}
          className="rounded-md bg-surface-3 px-2 py-1"
          data-affected-record-row=""
          data-record-id={rowRecordId(row, index)}
        >
          {rowLabel(row, index)}
        </span>
      ))}
      {remaining > 0 ? (
        <span className="rounded-md bg-surface-3 px-2 py-1">+{remaining} more</span>
      ) : null}
    </div>
  )
}

function BusinessChangeList({ groups = [] }) {
  const safeGroups = Array.isArray(groups) ? groups : []
  if (!safeGroups.length) return null
  return (
    <div className="mt-2 space-y-1.5" data-business-change-list="">
      {safeGroups.map((group, index) => {
        const label = businessChangeLabel(group.business_change, `Change ${index + 1}`)
        const count = businessChangeCount(group)
        const summary = businessChangeSummary(group, label)
        return (
          <div
            key={`${label}-${index}`}
            className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-surface-2 px-2.5 py-2 text-xs text-ink-muted"
            data-business-change-group=""
            data-business-change-label={label}
            data-business-change-count={count}
            data-response-contract={safeText(group.contract) || undefined}
            data-entity-type={safeText(group.entity_type) || undefined}
            data-change-type={safeText(group.change_type) || undefined}
            data-source-state-basis={safeText(group.source_state_basis) || undefined}
            data-field-change-count={Array.isArray(group.field_changes) ? group.field_changes.length : undefined}
          >
            <span className="font-semibold text-ink-muted">{summary}</span>
          </div>
        )
      })}
    </div>
  )
}

function CleanAuditRows({ rows = [] }) {
  const safeRows = Array.isArray(rows) ? rows : []
  if (!safeRows.length) return null
  return (
    <div className="mt-2 divide-y divide-hairline overflow-hidden rounded-md border border-hairline bg-surface-1 text-[11px]">
      {safeRows.map((row, index) => {
        const recordId = rowRecordId(row, index)
        const change = safeText(row.change)
          || fieldChangeSummary(row.field_changes)
          || [row.previous_priority, row.new_priority || row.current_priority]
            .filter((value) => value != null && value !== '')
            .join(' -> ')
        const status = safeText(row.status || row.outcome)
        return (
          <div
            key={`${recordId}-${index}`}
            className="grid gap-1 px-2.5 py-2 text-ink sm:grid-cols-[minmax(8rem,1fr)_minmax(7rem,1fr)_auto]"
            data-affected-record-row=""
            data-record-id={recordId}
          >
            <span className="font-medium">{recordId}</span>
            {change ? <span className="text-ink-muted">{change}</span> : <span />}
            {status ? <span className="text-ink-subtle">{status}</span> : null}
          </div>
        )
      })}
    </div>
  )
}

function CleanAuditDisclosure({ groups = [], totalCount = 0, defaultCollapsed = true, blockId = null }) {
  const safeGroups = Array.isArray(groups) ? groups : []
  if (!safeGroups.length) return null
  return (
    <Disclosure
      className="mt-3 rounded-md border border-hairline bg-surface-2"
      summaryClassName="cursor-pointer px-3 py-2 text-xs font-medium text-ink-subtle"
      title={`Full clean audit (${totalCount})`}
      defaultCollapsed={defaultCollapsed}
      data-clean-audit=""
      key={blockId || 'clean-audit'}
    >
      <div className="space-y-3 border-t border-hairline px-3 py-3" data-clean-audit-content="">
        {safeGroups.map((group, index) => {
          const label = businessChangeLabel(group.business_change, `Change ${index + 1}`)
          const count = businessChangeCount(group)
          return (
            <section
              key={`${label}-${index}`}
              data-clean-audit-group=""
              data-business-change-label={label}
              data-business-change-count={count}
              data-response-contract={safeText(group.contract) || undefined}
              data-entity-type={safeText(group.entity_type) || undefined}
              data-change-type={safeText(group.change_type) || undefined}
              data-source-state-basis={safeText(group.source_state_basis) || undefined}
              data-field-change-count={Array.isArray(group.field_changes) ? group.field_changes.length : undefined}
            >
              <div className="text-xs font-semibold text-ink">{businessChangeSummary(group, label)}</div>
              <CleanAuditRows rows={group.rows} />
            </section>
          )
        })}
      </div>
    </Disclosure>
  )
}

function redactTechnicalText(value) {
  return String(value == null ? '' : value)
    .replace(TECHNICAL_REDACTION_RE, (match) => {
      const key = match.split(/[:=\s]/)[0] || 'secret'
      return `${key}=[redacted]`
    })
    .replace(/traceback\s+\(most recent call last\):[\s\S]*/i, '[stack trace redacted]')
}

function formatDiagnosticValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => formatDiagnosticValue(item)).join(', ')
  }
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .slice(0, 6)
      .map(([key, item]) => `${humanizeResponseDocumentKey(key)}: ${formatDiagnosticValue(item)}`)
      .join('; ')
  }
  return redactTechnicalText(value)
}

function CompactCard({ title, children, tone = 'default', blockType = null, blockId = null, contract = null, entityType = null }) {
  const toneClass = tone === 'error'
    ? 'border-hairline bg-surface-1'
    : tone === 'warning'
      ? 'border-hairline bg-surface-1'
      : 'border-hairline bg-surface-1'
  return (
    <div
      className={`mt-3 min-w-0 max-w-full rounded-md border px-3 py-3 text-sm ${toneClass}`}
      data-response-block-type={blockType || undefined}
      data-response-block-id={blockId || undefined}
      data-response-contract={safeText(contract) || undefined}
      data-entity-type={safeText(entityType) || undefined}
    >
      {title ? <div className="text-sm font-semibold text-ink">{title}</div> : null}
      {children}
    </div>
  )
}

function Disclosure({ title, children, defaultCollapsed = true, className = '', summaryClassName = '', ...detailsProps }) {
  const [open, setOpen] = useState(defaultCollapsed === false)
  return (
    <details
      className={className}
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      {...detailsProps}
    >
      <summary className={summaryClassName}>{title}</summary>
      {children}
    </details>
  )
}

function ExpandableTable({ title, rows, defaultCollapsed = true, blockId = null }) {
  const presentation = tablePresentationFromResponseRows(rows, title)
  if (!presentation) return null
  if (!defaultCollapsed) {
    return <TablePresentation presentation={presentation} />
  }
  return (
    <Disclosure
      className="mt-2 rounded-md border border-hairline bg-surface-2"
      summaryClassName="cursor-pointer px-3 py-2 text-xs font-medium text-ink-subtle"
      title={`${title} (${rows.length})`}
      defaultCollapsed={defaultCollapsed}
      key={blockId || title}
    >
      <div className="max-h-80 overflow-auto border-t border-hairline">
        <TablePresentation presentation={presentation} defaultCollapsed={false} />
      </div>
    </Disclosure>
  )
}

function citationKey(value) {
  return safeText(value?.citation_id || value?.citationId || value?.source_id || value?.sourceId || value?.doc_id || value?.docId || value?.source_number || value?.sourceNumber)
}

function citationFromSource(source) {
  if (!source || typeof source !== 'object') return null
  const sourceId = safeText(source.source_id || source.sourceId || source.doc_id || source.docId)
  const sourceNumber = source.source_number || source.sourceNumber
  const citationId = safeText(source.citation_id || source.citationId) || `citation:${sourceId || sourceNumber || 'source'}`
  return {
    ...source,
    contract: safeText(source.contract) === 'source_citation_v1' ? 'source_citation_v1' : 'source_citation_v1',
    citation_id: citationId,
    source_id: sourceId,
    source_number: sourceNumber,
    doc_id: safeText(source.doc_id || source.docId),
    chunk_id: safeText(source.chunk_id || source.chunkId),
    title: safeText(source.title || source.doc_id || source.docId || `Source ${sourceNumber || ''}`),
    organization: safeText(source.organization),
    snippet: safeText(source.snippet),
    page: source.page,
    page_label: safeText(source.page_label || source.pageLabel),
    pdf_url: safeText(source.pdf_url || source.pdfUrl),
    bbox: source.bbox || source.bounding_box || source.boundingBox || null,
    char_range: source.char_range || source.charRange || source.text_range || source.textRange || null,
    text_search: safeText(source.text_search || source.textSearch || source.highlight_text || source.highlightText),
    policy_only: Boolean(source.policy_only || source.policyOnly),
  }
}

function sourceLocationLabel(source) {
  const page = safeText(source?.page)
  const chunk = safeText(source?.chunk_id || source?.chunkId)
  if (page && chunk) return `Page ${page} / Chunk ${chunk}`
  if (page) return `Page ${page}`
  if (chunk) return `Chunk ${chunk}`
  return null
}

function normalCharRange(value) {
  if (Array.isArray(value) && value.length >= 2) {
    const start = Number(value[0])
    const end = Number(value[1])
    if (Number.isFinite(start) && Number.isFinite(end) && end >= start) return { start, end }
  }
  if (value && typeof value === 'object') {
    const start = Number(value.start ?? value.from ?? value[0])
    const end = Number(value.end ?? value.to ?? value[1])
    if (Number.isFinite(start) && Number.isFinite(end) && end >= start) return { start, end }
  }
  return null
}

function appendPdfFragment(url, params) {
  const entries = Object.entries(params).filter(([, value]) => value != null && value !== '')
  if (!entries.length) return url
  const fragment = new URLSearchParams(entries.map(([key, value]) => [key, String(value)])).toString()
  const separator = url.includes('#') ? '&' : '#'
  return `${url}${separator}${fragment}`
}

function sourceOpenTarget(source) {
  const url = safeText(source?.pdf_url || source?.pdfUrl)
  if (!url) return { mode: 'drawer', href: null, highlightKind: null }
  const page = safeText(source?.page)
  const charRange = normalCharRange(source?.char_range || source?.charRange)
  const bbox = source?.bbox || source?.bounding_box || source?.boundingBox
  const searchText = safeText(source?.text_search || source?.textSearch || source?.snippet)
  if (charRange) {
    return {
      mode: 'exact',
      href: appendPdfFragment(url, {
        page,
        highlight: 'char_range',
        char_start: charRange.start,
        char_end: charRange.end,
      }),
      highlightKind: 'char_range',
    }
  }
  if (bbox) {
    return {
      mode: 'exact',
      href: appendPdfFragment(url, {
        page,
        highlight: 'bbox',
        bbox: JSON.stringify(bbox),
      }),
      highlightKind: 'bbox',
    }
  }
  if (page && searchText) {
    return {
      mode: 'search',
      href: appendPdfFragment(url, { page, search: searchText }),
      highlightKind: 'text_search',
    }
  }
  if (page) {
    return { mode: 'page', href: appendPdfFragment(url, { page }), highlightKind: null }
  }
  return { mode: 'pdf', href: url, highlightKind: null }
}

function SourceHoverCard({ source }) {
  if (!source) return null
  const location = sourceLocationLabel(source)
  return (
    <span
      role="tooltip"
      className="absolute left-0 top-full z-20 mt-1 w-72 max-w-[min(18rem,80vw)] rounded-md border border-hairline bg-surface-1 px-3 py-2 text-left text-[11px] font-normal text-ink shadow-lg"
      data-source-chip-hover=""
    >
      <span className="block font-semibold text-ink">{safeText(source.title) || 'Source'}</span>
      {source.organization ? <span className="mt-0.5 block text-ink-muted">{source.organization}</span> : null}
      {location ? <span className="mt-1 block text-ink-subtle">{location}</span> : null}
      {source.snippet ? <span className="mt-1.5 block text-ink-muted">{source.snippet}</span> : null}
    </span>
  )
}

function SourceChip({ citation, index, activeHoverId, setActiveHoverId, onOpenSource }) {
  const source = citationFromSource(citation)
  if (!source) return null
  const id = citationKey(source) || `citation:${index + 1}`
  const label = `[${source.source_number || index + 1}]`
  const openTarget = sourceOpenTarget(source)
  return (
    <span className="relative inline-flex align-baseline">
      <button
        type="button"
        className="mx-1 inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-hairline bg-surface-2 px-1.5 text-[11px] font-semibold leading-none text-primary hover:bg-surface-3 focus:outline-none focus:ring-2 focus:ring-primary/30"
        aria-label={`Open source ${source.source_number || index + 1}`}
        data-source-chip=""
        data-source-id={safeText(source.source_id) || undefined}
        data-doc-id={safeText(source.doc_id) || undefined}
        data-chunk-id={safeText(source.chunk_id) || undefined}
        data-source-number={safeText(source.source_number) || undefined}
        data-source-open-mode={openTarget.mode}
        data-source-highlight-kind={openTarget.highlightKind || undefined}
        onMouseEnter={() => setActiveHoverId(id)}
        onMouseLeave={() => setActiveHoverId((current) => (current === id ? null : current))}
        onFocus={() => setActiveHoverId(id)}
        onBlur={() => setActiveHoverId((current) => (current === id ? null : current))}
        onClick={() => onOpenSource?.(source)}
      >
        {label}
      </button>
      {activeHoverId === id ? <SourceHoverCard source={source} /> : null}
    </span>
  )
}

function SourceDrawer({ source, onClose }) {
  const safeSource = citationFromSource(source)
  if (!safeSource) return null
  const location = sourceLocationLabel(safeSource)
  const openTarget = sourceOpenTarget(safeSource)
  const pdfHref = openTarget.href
  return (
    <aside
      role="dialog"
      aria-label="Source details"
      className="mt-3 rounded-md border border-hairline bg-surface-1 px-3 py-3 text-sm"
      data-source-drawer=""
      data-source-id={safeText(safeSource.source_id) || undefined}
      data-doc-id={safeText(safeSource.doc_id) || undefined}
      data-chunk-id={safeText(safeSource.chunk_id) || undefined}
      data-source-open-mode={openTarget.mode}
      data-source-highlight-kind={openTarget.highlightKind || undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink">{safeSource.title || 'Source details'}</div>
          {safeSource.organization ? <div className="mt-0.5 text-xs text-ink-muted">{safeSource.organization}</div> : null}
        </div>
        <button
          type="button"
          className="rounded-md px-2 py-1 text-xs font-semibold text-ink-muted hover:bg-surface-2"
          onClick={onClose}
        >
          Close
        </button>
      </div>
      <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
        {safeSource.doc_id ? (
          <div className="min-w-0 rounded-md bg-surface-2 px-2.5 py-2">
            <dt className="font-semibold text-ink-muted">Document</dt>
            <dd className="mt-0.5 break-words text-ink">{safeSource.doc_id}</dd>
          </div>
        ) : null}
        {safeSource.chunk_id ? (
          <div className="min-w-0 rounded-md bg-surface-2 px-2.5 py-2">
            <dt className="font-semibold text-ink-muted">Chunk</dt>
            <dd className="mt-0.5 break-words text-ink">{safeSource.chunk_id}</dd>
          </div>
        ) : null}
        {location ? (
          <div className="min-w-0 rounded-md bg-surface-2 px-2.5 py-2">
            <dt className="font-semibold text-ink-muted">Location</dt>
            <dd className="mt-0.5 break-words text-ink">{location}</dd>
          </div>
        ) : null}
        {safeSource.source_number ? (
          <div className="min-w-0 rounded-md bg-surface-2 px-2.5 py-2">
            <dt className="font-semibold text-ink-muted">Citation</dt>
            <dd className="mt-0.5 break-words text-ink">Source {safeSource.source_number}</dd>
          </div>
        ) : null}
      </dl>
      {safeSource.snippet ? (
        <div className="mt-3 rounded-md bg-surface-2 px-3 py-2 text-xs text-ink" data-source-drawer-snippet="">
          {safeSource.snippet}
        </div>
      ) : null}
      {pdfHref ? (
        <a
          className="mt-3 inline-flex items-center rounded-md bg-surface-3 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-surface-2"
          href={pdfHref}
          target="_blank"
          rel="noreferrer"
          data-source-pdf-link=""
          data-source-open-mode={openTarget.mode}
          data-source-highlight-kind={openTarget.highlightKind || undefined}
        >
          {openTarget.mode === 'exact'
            ? 'Open highlighted PDF'
            : openTarget.mode === 'search'
              ? `Open PDF search on page ${safeSource.page}`
              : safeSource.page
                ? `Open PDF page ${safeSource.page}`
                : 'Open PDF'}
        </a>
      ) : null}
    </aside>
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
    <CompactCard title={block.title || 'Approval required'} blockType="approval_required" blockId={block.id}>
      <div className="mt-1 text-sm text-ink">{block.summary || 'Review the proposed change before it is applied.'}</div>
      <RowPreview rows={rows} limit={5} />
      {showApprovalActions ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={isDecidingApproval}
            aria-busy={isDecidingApproval ? 'true' : 'false'}
            onClick={() => decideApproval?.('approve', pendingApproval?.args, pendingApproval)}
            className="inline-flex min-w-[6.5rem] items-center justify-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-70"
          >
            {isDecidingApproval ? 'Approving...' : 'Approve'}
          </button>
          <button
            type="button"
            disabled={isDecidingApproval}
            onClick={() => decideApproval?.('reject', undefined, pendingApproval)}
            className="rounded-md bg-inverse-canvas px-3 py-1.5 text-xs font-semibold text-inverse-ink hover:opacity-90 disabled:opacity-60"
          >
            Reject
          </button>
        </div>
      ) : null}
      {rows.length > 5 ? (
        <ExpandableTable title="Affected records" rows={rows} defaultCollapsed={block.details_collapsed !== false} blockId={block.id} />
      ) : null}
    </CompactCard>
  )
}

function CompletedStepBlock({ block }) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Completed step'} blockType="completed_step" blockId={block.id}>
      <div className="mt-1 text-sm text-ink">{block.summary}</div>
      <RowPreview rows={rows} limit={3} />
      {rows.length > 3 ? (
        <ExpandableTable title="Completed records" rows={rows} defaultCollapsed={block.details_collapsed !== false} blockId={block.id} />
      ) : null}
    </CompactCard>
  )
}

function ResultSummaryBlock({ block }) {
  const steps = Array.isArray(block.steps) ? block.steps : []
  return (
    <CompactCard title={block.title || 'Result summary'} blockType="result_summary" blockId={block.id}>
      <div className="mt-1 text-sm text-ink" data-final-summary="">{block.summary}</div>
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
    <CompactCard
      title={block.title || 'Mutation result'}
      blockType="mutation_result"
      blockId={block.id}
      contract={block.contract}
    >
      <div className="mt-1 text-sm text-ink" data-final-summary="">{block.summary}</div>
      <RowPreview rows={rows} limit={block.preview_limit || PREVIEW_LIMIT} />
      {rows.length > 5 ? <ExpandableTable title="Affected records" rows={rows} blockId={block.id} /> : null}
    </CompactCard>
  )
}

function FinalBusinessResultBlock({ summaryBlock, mutationBlock }) {
  const groups = Array.isArray(mutationBlock?.groups) && mutationBlock.groups.length
    ? mutationBlock.groups
    : Array.isArray(summaryBlock?.steps)
      ? summaryBlock.steps
      : []
  const rows = Array.isArray(mutationBlock?.rows) ? mutationBlock.rows : []
  const previewLimit = Number.isFinite(Number(mutationBlock?.preview_limit))
    ? Number(mutationBlock.preview_limit)
    : PREVIEW_LIMIT
  const totalCount = Number.isFinite(Number(summaryBlock?.total_count))
    ? Number(summaryBlock.total_count)
    : rows.length

  return (
    <CompactCard
      title={summaryBlock?.title || 'Changes completed'}
      blockType="result_summary"
      blockId={summaryBlock?.id}
      contract={mutationBlock?.contract}
    >
      <div
        data-final-result-card=""
        data-response-block-type="mutation_result"
        data-response-block-id={mutationBlock?.id}
        data-response-contract={safeText(mutationBlock?.contract) || undefined}
      >
        <div className="mt-1 text-sm text-ink" data-final-summary="">
          {summaryBlock?.summary || mutationBlock?.summary}
        </div>
        <BusinessChangeList groups={groups} />
        <RowPreview rows={rows} limit={previewLimit} />
        <CleanAuditDisclosure
          groups={groups}
          totalCount={totalCount}
          defaultCollapsed={mutationBlock?.details_collapsed !== false}
          blockId={mutationBlock?.id}
        />
      </div>
    </CompactCard>
  )
}

function RecordPreviewBlock({ block }) {
  const rows = Array.isArray(block.rows) ? block.rows : []
  return (
    <CompactCard title={block.title || 'Records'} blockType="record_preview" blockId={block.id}>
      <RowPreview rows={rows} limit={5} />
      {rows.length > 5 ? <ExpandableTable title={block.title || 'Records'} rows={rows} defaultCollapsed={block.details_collapsed !== false} blockId={block.id} /> : null}
    </CompactCard>
  )
}

function SafetyNoticeBlock({ block }) {
  const safetyContent = safeText(block.safety_content || block.safetyContent || block.message || block.summary)
  if (!safetyContent) return null
  return (
    <CompactCard
      title={block.title || 'Safety notice'}
      tone="warning"
      blockType="safety_notice"
      blockId={block.id}
      contract={block.contract || 'safety_notice_v1'}
    >
      <div className="mt-1 text-sm text-ink" data-safety-notice-content="">{safetyContent}</div>
    </CompactCard>
  )
}

function KnowledgeAnswerBlock({ block, sourceLookup, activeHoverId, setActiveHoverId, onOpenSource }) {
  const blockCitations = Array.isArray(block.citations) ? block.citations : []
  const citationsById = new Map(sourceLookup)
  for (const citation of blockCitations) {
    const safeCitation = citationFromSource(citation)
    const key = citationKey(safeCitation)
    if (key) citationsById.set(key, safeCitation)
  }
  const segments = Array.isArray(block.segments) && block.segments.length
    ? block.segments
    : [{ text: safeText(block.answer), citation_ids: blockCitations.map((citation) => citationKey(citationFromSource(citation))).filter(Boolean) }]
  return (
    <CompactCard
      title={block.title || 'Procedure guidance'}
      blockType="knowledge_answer"
      blockId={block.id}
      contract={block.contract || 'knowledge_answer_v1'}
    >
      <div className="mt-1 whitespace-pre-wrap break-words text-sm text-ink" data-knowledge-answer="">
        {segments.map((segment, segmentIndex) => {
          const text = safeText(segment.text)
          if (!text) return null
          const citationIds = Array.isArray(segment.citation_ids || segment.citationIds)
            ? (segment.citation_ids || segment.citationIds).map((item) => safeText(item)).filter(Boolean)
            : []
          const citations = citationIds.map((id) => citationsById.get(id)).filter(Boolean)
          return (
            <span key={`${block.id}:segment:${segmentIndex}`}>
              {segmentIndex > 0 ? ' ' : ''}
              {text}
              {citations.map((citation, citationIndex) => (
                <SourceChip
                  key={`${citationKey(citation)}:${citationIndex}`}
                  citation={citation}
                  index={citationIndex}
                  activeHoverId={activeHoverId}
                  setActiveHoverId={setActiveHoverId}
                  onOpenSource={onOpenSource}
                />
              ))}
            </span>
          )
        })}
      </div>
    </CompactCard>
  )
}

function SourceListBlock({ block }) {
  const sources = Array.isArray(block.sources) ? block.sources : []
  if (!sources.length) return null
  return (
    <CompactCard title={block.title || 'Knowledge sources'} blockType="source_list" blockId={block.id} contract={block.contract || 'source_list_v1'}>
      <div className="mt-2 space-y-2 text-xs text-ink-muted">
        {sources.map((source, index) => {
          const title = safeText(source.title || source.doc_id || `Source ${index + 1}`)
          const snippet = safeText(source.snippet)
          return (
            <div
              key={`${source.source_id || source.doc_id || title}-${index}`}
              className="rounded-md bg-surface-2 px-2.5 py-2"
              data-response-contract={safeText(source.contract) || undefined}
              data-source-id={safeText(source.source_id) || undefined}
              data-doc-id={safeText(source.doc_id) || undefined}
              data-chunk-id={safeText(source.chunk_id) || undefined}
            >
              <div className="font-semibold text-ink">{title}</div>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                {['doc_id', 'chunk_id', 'page', 'machine_id', 'organization'].map((key) => (
                  source[key] ? <span key={key}>{humanizeResponseDocumentKey(key)}: {String(source[key])}</span> : null
                ))}
              </div>
              {snippet ? <div className="mt-1.5 line-clamp-2 text-ink-subtle">{snippet}</div> : null}
            </div>
          )
        })}
      </div>
    </CompactCard>
  )
}

function StatusResultBlock({ block, documentMessage }) {
  const fields = Array.isArray(block.fields) ? block.fields : []
  const secondaryFields = Array.isArray(block.secondary_fields) ? block.secondary_fields : []
  const summary = safeText(block.summary)
  const shouldShowSummary = summary && summary !== safeText(documentMessage)
  return (
    <CompactCard
      title={block.title || 'Status'}
      blockType="status_result"
      blockId={block.id}
      contract={block.contract}
      entityType={block.entity_type}
    >
      {shouldShowSummary ? <div className="mt-1 text-sm text-ink">{summary}</div> : null}
      {fields.length ? (
        <dl className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
          {fields.map((field, index) => (
            <div key={`${field.key || field.label}-${index}`} className="min-w-0 rounded-md bg-surface-2 px-2.5 py-2">
              <dt className="font-semibold text-ink-muted">{field.label}</dt>
              <dd className="mt-0.5 break-words text-ink">{String(field.value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {secondaryFields.length ? (
        <Disclosure
          className="mt-3 rounded-md border border-hairline bg-surface-2"
          summaryClassName="cursor-pointer px-3 py-2 text-xs font-medium text-ink-subtle"
          title="Technical details"
          defaultCollapsed={block.details_collapsed !== false}
        >
          <dl className="grid gap-2 border-t border-hairline px-3 py-3 text-xs sm:grid-cols-2">
            {secondaryFields.map((field, index) => (
              <div key={`${field.key || field.label}-${index}`} className="min-w-0">
                <dt className="font-semibold text-ink-muted">{field.label}</dt>
                <dd className="mt-0.5 break-words text-ink">{String(field.value)}</dd>
              </div>
            ))}
          </dl>
        </Disclosure>
      ) : null}
    </CompactCard>
  )
}

function DiagnosticBlock({ block }) {
  const technicalDetails = block.technical_details && typeof block.technical_details === 'object'
    ? block.technical_details
    : {}
  return (
    <CompactCard title={block.title || 'Needs attention'} tone={block.severity === 'error' ? 'error' : 'warning'} blockType="diagnostic" blockId={block.id}>
      <div className="mt-1 text-sm text-ink">{block.user_message || block.summary || 'The request could not be completed.'}</div>
      <div className="mt-2 space-y-1 text-xs text-ink-muted">
        {block.cause ? <div><span className="font-semibold text-ink-muted">Cause:</span> {block.cause}</div> : null}
        {block.current_state ? <div><span className="font-semibold text-ink-muted">Current state:</span> {block.current_state}</div> : null}
        {block.next_action ? <div><span className="font-semibold text-ink-muted">Next action:</span> {block.next_action}</div> : null}
      </div>
      {block.impact && Object.keys(block.impact).length ? (
        <Disclosure
          className="mt-2"
          summaryClassName="cursor-pointer text-xs font-medium text-ink-subtle"
          title="Impact details"
        >
          <div className="mt-2 space-y-1 text-xs text-ink-muted">
            {Object.entries(block.impact).slice(0, 8).map(([key, value]) => (
              <div key={key}>
                <span className="font-semibold text-ink-muted">{humanizeResponseDocumentKey(key)}:</span>{' '}
                {formatDiagnosticValue(value)}
              </div>
            ))}
          </div>
        </Disclosure>
      ) : null}
      <Disclosure
        className="mt-2"
        summaryClassName="cursor-pointer text-xs font-medium text-ink-subtle"
        title="Technical details"
        defaultCollapsed={block.details_collapsed !== false}
      >
        <div className="mt-2 rounded-md bg-surface-2 px-2.5 py-2 text-xs text-ink-muted">
          {Object.keys(technicalDetails).length ? (
            Object.entries(technicalDetails).slice(0, 12).map(([key, value]) => (
              <div key={key} className="break-words">
                <span className="font-semibold">{humanizeResponseDocumentKey(key)}:</span>{' '}
                {formatDiagnosticValue(value)}
              </div>
            ))
          ) : (
            <div>No technical details were provided.</div>
          )}
        </div>
      </Disclosure>
    </CompactCard>
  )
}

function renderBlock(block, props) {
  if (!block || block.type === 'run_activity' || block.type === 'short_message') return null
  if (block.type === 'approval_required') return <ApprovalBlock key={block.id} block={block} {...props} />
  if (block.type === 'completed_step') return <CompletedStepBlock key={block.id} block={block} />
  if (block.type === 'result_summary') return <ResultSummaryBlock key={block.id} block={block} />
  if (block.type === 'mutation_result') return <MutationResultBlock key={block.id} block={block} />
  if (block.type === 'result_table') return <ExpandableTable key={block.id} title={block.title || 'Affected records'} rows={block.rows} defaultCollapsed blockId={block.id} />
  if (block.type === 'status_result') return <StatusResultBlock key={block.id} block={block} documentMessage={props.documentMessage} />
  if (block.type === 'record_preview') return <RecordPreviewBlock key={block.id} block={block} />
  if (block.type === 'safety_notice') return <SafetyNoticeBlock key={block.id} block={block} />
  if (block.type === 'knowledge_answer') return <KnowledgeAnswerBlock key={block.id} block={block} {...props} />
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
  const [activeSource, setActiveSource] = useState(null)
  const [activeHoverId, setActiveHoverId] = useState(null)
  const sourceLookup = useMemo(() => {
    const lookup = new Map()
    for (const block of document?.blocks || []) {
      if (block?.type !== 'source_list' || !Array.isArray(block.sources)) continue
      for (const source of block.sources) {
        const citation = citationFromSource(source)
        const key = citationKey(citation)
        if (key) lookup.set(key, citation)
        const sourceId = safeText(citation?.source_id)
        if (sourceId) lookup.set(`citation:${sourceId}`, citation)
        const number = safeText(citation?.source_number)
        if (number) lookup.set(`citation:${number}`, citation)
      }
    }
    return lookup
  }, [document])
  if (!document) return null
  const activitySteps = activityStepsFromResponseDocument(document)
  const message = responseDocumentMessage(document)
  const finalSummaryBlock = (document.blocks || []).find((block) =>
    block?.type === 'result_summary' &&
    block.status === 'completed',
  )
  const finalMutationBlock = (document.blocks || []).find((block) =>
    block?.type === 'mutation_result' &&
    block.status === 'completed' &&
    Array.isArray(block.groups) &&
    block.groups.length > 0 &&
    hasSupportedMutationContract(block),
  )
  const shouldRenderFinalBusinessResult = Boolean(finalSummaryBlock && finalMutationBlock)
  const duplicateTableOwners = useMemo(() => {
    const approvalOwners = new Set()
    const mutationOwners = new Set()
    for (const block of document.blocks || []) {
      const approvalId = block.approval_id || ''
      const operationId = block.operation_id || ''
      if (block?.type === 'approval_required') approvalOwners.add(`${approvalId}:${operationId}`)
      if (block?.type === 'mutation_result') mutationOwners.add(`${approvalId}:${operationId}`)
    }
    return { approvalOwners, mutationOwners }
  }, [document])
  const renderedBlocks = (document.blocks || [])
    .filter((block) => {
      if (!['result_table', 'record_preview'].includes(block?.type)) return true
      const ownerKey = `${block.approval_id || ''}:${block.operation_id || ''}`
      if (duplicateTableOwners.approvalOwners.has(ownerKey)) return false
      if (
        block.type === 'result_table' &&
        duplicateTableOwners.mutationOwners.has(ownerKey) &&
        Array.isArray(block.rows) &&
        block.rows.length > PREVIEW_LIMIT
      ) {
        return false
      }
      return true
    })
    .flatMap((block) => {
      if (shouldRenderFinalBusinessResult && block === finalSummaryBlock) {
        return [(
          <FinalBusinessResultBlock
            key={`${finalSummaryBlock.id}:${finalMutationBlock.id}`}
            summaryBlock={finalSummaryBlock}
            mutationBlock={finalMutationBlock}
          />
        )]
      }
      if (shouldRenderFinalBusinessResult && block === finalMutationBlock) return []
      return [renderBlock(block, {
        pendingApproval,
        showApprovalActions,
        decideApproval,
        isDecidingApproval,
        documentMessage: message,
        sourceLookup,
        activeHoverId,
        setActiveHoverId,
        onOpenSource: setActiveSource,
      })]
    })
    .filter(Boolean)

  return (
    <div className="min-w-0 max-w-full" data-response-document-root="">
      <ActivityTimeline steps={activitySteps} />
      {message ? <div className="whitespace-pre-wrap break-words text-ink">{message}</div> : null}
      {renderedBlocks}
      <SourceDrawer source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  )
}
