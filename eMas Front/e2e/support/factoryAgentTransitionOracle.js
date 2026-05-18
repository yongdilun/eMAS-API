import fs from 'node:fs'
import path from 'node:path'

import { expect } from '@playwright/test'

import { redactSensitiveArtifactText } from './artifactRedaction.js'

const PASS = '__factory_agent_transition_pass__'

export const uiStatusByBackendStatus = Object.freeze({
  PLANNING: 'Understanding',
  EXECUTING: 'Checking',
  WAITING_APPROVAL: 'Waiting for approval',
  WAITING_CONFIRMATION: 'Waiting for confirmation',
  BLOCKED: 'Needs attention',
  FAILED: 'Needs attention',
  COMPLETED: 'Complete',
  IDLE: 'Ready',
})

const statusLabels = Object.freeze([
  'Ready',
  'Understanding',
  'Checking',
  'Waiting for approval',
  'Waiting for confirmation',
  'Needs attention',
  'Complete',
  'Working',
])

export const baseForbiddenTransitionText = Object.freeze([
  { label: 'internal non_terminal_snapshot reason', pattern: /non_terminal_snapshot/i },
  { label: 'orphan idle diagnostic', pattern: /Session status:\s*IDLE/i },
  {
    label: 'generic needs-attention diagnostic',
    pattern: /Needs attention\s+The request needs attention before it can continue/i,
  },
  { label: 'raw JSON object', pattern: /(?:^|\n)\s*[\[{]\s*"[^"\n]+"\s*:/ },
  { label: 'traceback or stack trace', pattern: /Traceback|stack trace|^\s*at\s+\S+.*:\d+:\d+/im },
  {
    label: 'secret or token diagnostic',
    pattern: /\b(?:api[_-]?key|authorization|bearer|password|secret|token)\b\s*[:=]\s*(?!\[redacted\])[\w.+/=-]{6,}/i,
  },
  { label: 'known secret sample', pattern: /\b(?:sk-[a-z0-9_-]{12,}|raw-secret-token|super-secret)\b/i },
])

function asArray(value) {
  if (value === undefined || value === null) return []
  return Array.isArray(value) ? value : [value]
}

function uniq(values) {
  return [...new Set(values.filter((value) => value !== undefined && value !== null))]
}

function matches(value, pattern) {
  const text = String(value || '')
  if (pattern instanceof RegExp) return pattern.test(text)
  return text.includes(String(pattern))
}

function labelForPattern(pattern) {
  if (pattern?.label) return pattern.label
  if (pattern instanceof RegExp) return String(pattern)
  return JSON.stringify(pattern)
}

function compactText(value, limit = 900) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  if (text.length <= limit) return text
  return `${text.slice(0, limit)}...`
}

function blockTextSummary(blocks, type) {
  return blocks
    .filter((block) => block.type === type)
    .map((block) => ({
      id: block.id || null,
      text: compactText(block.text, 400),
      hasApprove: block.hasApprove,
      hasReject: block.hasReject,
    }))
}

function backendSummary(snapshot) {
  const document = snapshot?.response_document || {}
  const blocks = Array.isArray(document.blocks) ? document.blocks : []
  return {
    sessionStatus: snapshot?.session?.status || null,
    phase: snapshot?.phase || null,
    pendingApprovalId: snapshot?.pending_approval?.approval_id || null,
    responseDocumentState: document.state || null,
    responseDocumentRevision: document.revision ?? null,
    responseDocumentCurrentStepId: document.current_step_id || null,
    responseBlockTypes: blocks.map((block) => block?.type).filter(Boolean),
    responseApprovalIds: blocks.map((block) => block?.approval_id).filter(Boolean),
  }
}

function uiSummary(ui) {
  return {
    headerStatus: ui.headerStatus || null,
    activeSidebarStatus: ui.activeSidebarStatus || null,
    visibleBlockTypes: ui.visibleBlockTypes || [],
    visibleBlockIds: ui.visibleBlockIds || [],
    approvalActionLabels: ui.approvalActionLabels || [],
    approvalTexts: blockTextSummary(ui.visibleBlocks || [], 'approval_required'),
    resultTexts: [
      ...blockTextSummary(ui.visibleBlocks || [], 'result_summary'),
      ...blockTextSummary(ui.visibleBlocks || [], 'mutation_result'),
    ],
    diagnosticTexts: blockTextSummary(ui.visibleBlocks || [], 'diagnostic'),
    assistantText: compactText(ui.latestAssistantText, 900),
  }
}

export function summarizeTransitionProbe(probe) {
  return {
    checkpoint: probe.checkpoint || null,
    backend: backendSummary(probe.snapshot),
    ui: uiSummary(probe.ui || {}),
  }
}

function expectedStatuses(expected) {
  const statuses = asArray(expected.sessionStatuses || expected.sessionStatus)
  return statuses.length ? statuses : null
}

function expectedResponseStates(expected) {
  const states = asArray(expected.responseStates || expected.responseState)
  return states.length ? states : null
}

function expectedUiStatuses(statuses) {
  if (!statuses) return null
  return uniq(statuses.map((status) => uiStatusByBackendStatus[status] || null))
}

function addForbiddenTextViolations(violations, text, expected) {
  const forbidden = [...baseForbiddenTransitionText, ...asArray(expected.forbiddenText)]
  if (expected.forbidWaitingApproval1) {
    forbidden.push({ label: 'stale Waiting for approval 1 after approval 1 was decided', pattern: /Waiting for approval 1/i })
  }
  if (expected.forbidApprovalRequired) {
    forbidden.push({ label: 'stale Approval required after completion', pattern: /Approval required/i })
  }
  for (const item of forbidden) {
    const pattern = item?.pattern || item
    if (matches(text, pattern)) {
      violations.push(`forbidden visible text matched ${item?.label || labelForPattern(pattern)}`)
    }
  }
}

function addTextExpectationViolations(violations, text, expected) {
  for (const pattern of asArray(expected.textIncludes)) {
    if (!matches(text, pattern)) violations.push(`visible text did not include ${labelForPattern(pattern)}`)
  }
  for (const pattern of asArray(expected.textExcludes)) {
    if (matches(text, pattern)) violations.push(`visible text unexpectedly included ${labelForPattern(pattern)}`)
  }
}

function addListExpectationViolations(violations, actualValues, requiredValues, label) {
  const actual = new Set(actualValues || [])
  for (const value of asArray(requiredValues)) {
    if (!actual.has(value)) violations.push(`${label} missing ${value}`)
  }
}

function addAbsentListExpectationViolations(violations, actualValues, forbiddenValues, label) {
  const actual = new Set(actualValues || [])
  for (const value of asArray(forbiddenValues)) {
    if (actual.has(value)) violations.push(`${label} still contained ${value}`)
  }
}

export function evaluateTransitionProbe(probe, expected = {}) {
  const violations = []
  const snapshot = probe.snapshot || {}
  const document = snapshot.response_document || {}
  const ui = probe.ui || {}
  const backend = backendSummary(snapshot)
  const sessionStatuses = expectedStatuses(expected)
  const responseStates = expectedResponseStates(expected)

  if (sessionStatuses && !sessionStatuses.includes(backend.sessionStatus)) {
    violations.push(`backend session.status expected ${sessionStatuses.join(' or ')} but saw ${backend.sessionStatus || '<missing>'}`)
  }
  if (responseStates && !responseStates.includes(backend.responseDocumentState)) {
    violations.push(`response_document.state expected ${responseStates.join(' or ')} but saw ${backend.responseDocumentState || '<missing>'}`)
  }
  if (Object.hasOwn(expected, 'pendingApprovalId') && backend.pendingApprovalId !== (expected.pendingApprovalId || null)) {
    violations.push(`pending_approval.approval_id expected ${expected.pendingApprovalId || '<none>'} but saw ${backend.pendingApprovalId || '<none>'}`)
  }
  if (expected.pendingApprovalMustDifferFrom && backend.pendingApprovalId === expected.pendingApprovalMustDifferFrom) {
    violations.push(`pending_approval.approval_id was still stale ${backend.pendingApprovalId}`)
  }
  if (Object.hasOwn(expected, 'revisionGreaterThan')) {
    const revision = Number(document.revision)
    if (!Number.isFinite(revision) || revision <= Number(expected.revisionGreaterThan)) {
      violations.push(`response_document.revision expected > ${expected.revisionGreaterThan} but saw ${document.revision ?? '<missing>'}`)
    }
  }
  if (Object.hasOwn(expected, 'minRevision')) {
    const revision = Number(document.revision)
    if (!Number.isFinite(revision) || revision < Number(expected.minRevision)) {
      violations.push(`response_document.revision expected >= ${expected.minRevision} but saw ${document.revision ?? '<missing>'}`)
    }
  }

  const derivedUiStatuses = expectedUiStatuses(sessionStatuses)
  const headerStatuses = asArray(expected.headerStatuses || expected.headerStatus)
  const sidebarStatuses = asArray(expected.sidebarStatuses || expected.sidebarStatus)
  const allowedHeaderStatuses = headerStatuses.length ? headerStatuses : derivedUiStatuses
  const allowedSidebarStatuses = sidebarStatuses.length ? sidebarStatuses : derivedUiStatuses

  if (allowedHeaderStatuses?.length && !allowedHeaderStatuses.includes(ui.headerStatus)) {
    violations.push(`visible header status expected ${allowedHeaderStatuses.join(' or ')} but saw ${ui.headerStatus || '<missing>'}`)
  }
  if (allowedSidebarStatuses?.length && !allowedSidebarStatuses.includes(ui.activeSidebarStatus)) {
    violations.push(`active sidebar status expected ${allowedSidebarStatuses.join(' or ')} but saw ${ui.activeSidebarStatus || '<missing>'}`)
  }

  addListExpectationViolations(violations, ui.visibleBlockTypes, expected.visibleBlockTypes, 'visible block types')
  addAbsentListExpectationViolations(violations, ui.visibleBlockTypes, expected.hiddenBlockTypes, 'visible block types')
  addListExpectationViolations(violations, ui.visibleBlockIds, expected.visibleBlockIds, 'visible block ids')
  addAbsentListExpectationViolations(violations, ui.visibleBlockIds, expected.hiddenBlockIds, 'visible block ids')
  addListExpectationViolations(violations, backend.responseBlockTypes, expected.backendBlockTypes, 'response_document block types')
  addAbsentListExpectationViolations(violations, backend.responseBlockTypes, expected.hiddenBackendBlockTypes, 'response_document block types')

  if (Object.hasOwn(expected, 'approvalActionCount')) {
    const count = ui.approvalActionLabels.length
    if (count !== expected.approvalActionCount) {
      violations.push(`visible approval action count expected ${expected.approvalActionCount} but saw ${count}`)
    }
  }

  const text = ui.visibleText || ''
  addForbiddenTextViolations(violations, text, {
    ...expected,
    forbidApprovalRequired:
      expected.forbidApprovalRequired ||
      expected.sessionStatus === 'COMPLETED' ||
      expected.responseState === 'completed',
  })
  addTextExpectationViolations(violations, text, expected)

  return {
    ok: violations.length === 0,
    violations,
    summary: summarizeTransitionProbe(probe),
  }
}

export function formatTransitionFailure({ checkpoint, expected, result }) {
  return JSON.stringify({
    checkpoint,
    violations: result.violations,
    expected: {
      sessionStatus: expected.sessionStatus || expected.sessionStatuses || null,
      responseState: expected.responseState || expected.responseStates || null,
      pendingApprovalId: Object.hasOwn(expected, 'pendingApprovalId') ? expected.pendingApprovalId || null : undefined,
      visibleBlockTypes: expected.visibleBlockTypes || undefined,
      hiddenBlockTypes: expected.hiddenBlockTypes || undefined,
      textIncludes: asArray(expected.textIncludes).map(labelForPattern),
      textExcludes: asArray(expected.textExcludes).map(labelForPattern),
    },
    ...result.summary,
  }, null, 2)
}

function safeArtifactName(value) {
  return String(value || 'transition-checkpoint')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 90) || 'transition-checkpoint'
}

async function attachTransitionArtifact(testInfo, checkpoint, payload) {
  if (!testInfo) return
  const name = `${safeArtifactName(checkpoint)}-transition-oracle.json`
  const body = redactSensitiveArtifactText(payload)
  const artifactPath = testInfo.outputPath(name)
  fs.mkdirSync(path.dirname(artifactPath), { recursive: true })
  fs.writeFileSync(artifactPath, body)
  await testInfo.attach(name, {
    path: artifactPath,
    contentType: 'application/json',
  })
}

export async function collectVisibleTransitionUi(page) {
  return page.evaluate((labels) => {
    const statusSet = new Set(labels)
    const dialog = document.querySelector('[role="dialog"]') || document.body
    const heading = dialog.querySelector('h2')
    const headerRegion = heading?.parentElement || dialog
    const headerStatus = Array.from(headerRegion.querySelectorAll('span'))
      .map((node) => (node.textContent || '').trim())
      .find((value) => statusSet.has(value)) || null
    const activeSessionButton = dialog.querySelector('aside [aria-current="page"]')
    const activeSidebarStatus = activeSessionButton
      ? Array.from(activeSessionButton.querySelectorAll('span'))
        .map((node) => (node.textContent || '').trim())
        .find((value) => statusSet.has(value)) || null
      : null
    const roots = Array.from(dialog.querySelectorAll('[data-response-document-root]'))
    const latestRoot = roots[roots.length - 1] || dialog
    const visibleBlocks = Array.from(latestRoot.querySelectorAll('[data-response-block-type]')).map((node) => {
      const text = node.innerText || node.textContent || ''
      return {
        type: node.getAttribute('data-response-block-type') || null,
        id: node.getAttribute('data-response-block-id') || null,
        text,
        hasApprove: Array.from(node.querySelectorAll('button')).some((button) => (button.textContent || '').trim() === 'Approve'),
        hasReject: Array.from(node.querySelectorAll('button')).some((button) => (button.textContent || '').trim() === 'Reject'),
      }
    })
    const approvalActionLabels = Array.from(latestRoot.querySelectorAll('button'))
      .map((button) => (button.textContent || '').trim())
      .filter((label) => label === 'Approve' || label === 'Reject')
    return {
      headerStatus,
      activeSidebarStatus,
      visibleBlockTypes: visibleBlocks.map((block) => block.type).filter(Boolean),
      visibleBlockIds: visibleBlocks.map((block) => block.id).filter(Boolean),
      visibleBlocks,
      approvalActionLabels,
      latestAssistantText: latestRoot.innerText || latestRoot.textContent || '',
      visibleText: dialog.innerText || document.body.innerText || '',
    }
  }, statusLabels)
}

export async function collectTransitionProbe(page, { checkpoint, snapshotForPage }) {
  if (typeof snapshotForPage !== 'function') {
    throw new Error('collectTransitionProbe requires snapshotForPage(page)')
  }
  const [snapshot, ui] = await Promise.all([
    snapshotForPage(page),
    collectVisibleTransitionUi(page),
  ])
  return { checkpoint, snapshot, ui }
}

export async function expectTransitionCheckpoint(page, {
  checkpoint,
  snapshotForPage,
  expected,
  testInfo = null,
  timeout = 10_000,
}) {
  let lastResult = null
  let lastProbe = null
  try {
    await expect
      .poll(async () => {
        lastProbe = await collectTransitionProbe(page, { checkpoint, snapshotForPage })
        lastResult = evaluateTransitionProbe(lastProbe, expected)
        return lastResult.ok ? PASS : formatTransitionFailure({ checkpoint, expected, result: lastResult })
      }, {
        timeout,
        message: `Factory Agent transition checkpoint did not converge: ${checkpoint}`,
      })
      .toBe(PASS)
  } catch (error) {
    const payload = lastResult
      ? formatTransitionFailure({ checkpoint, expected, result: lastResult })
      : JSON.stringify({ checkpoint, error: error?.message || String(error), probe: lastProbe }, null, 2)
    await attachTransitionArtifact(testInfo, checkpoint, payload)
    throw new Error(`Factory Agent transition checkpoint failed: ${checkpoint}\n${payload}`)
  }
  return lastResult.summary
}
