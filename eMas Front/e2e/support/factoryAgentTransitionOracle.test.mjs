import assert from 'node:assert/strict'
import test from 'node:test'

import {
  evaluateTransitionProbe,
  formatTransitionFailure,
  summarizeTransitionProbe,
} from './factoryAgentTransitionOracle.js'

function probe(overrides = {}) {
  return {
    checkpoint: 'after approval',
    snapshot: {
      session: { status: 'WAITING_APPROVAL' },
      phase: 'WAITING_APPROVAL',
      pending_approval: { approval_id: 'approval-2' },
      response_document: {
        state: 'waiting_approval',
        revision: 8,
        current_step_id: 'approval-2',
        blocks: [
          { type: 'completed_step', approval_id: 'approval-1' },
          { type: 'approval_required', approval_id: 'approval-2' },
        ],
      },
    },
    ui: {
      headerStatus: 'Waiting for approval',
      activeSidebarStatus: 'Waiting for approval',
      visibleBlockTypes: ['completed_step', 'approval_required'],
      visibleBlockIds: ['completed-step:approval-1', 'approval:approval-2'],
      approvalActionLabels: ['Approve', 'Reject'],
      visibleBlocks: [
        { type: 'completed_step', id: 'completed-step:approval-1', text: 'Completed step Updated 10 jobs.' },
        { type: 'approval_required', id: 'approval:approval-2', text: 'Approval required Update 11 jobs.' },
      ],
      latestAssistantText: 'Done. Please review approval 2 before I update original high-priority jobs.',
      visibleText: 'Done. Please review approval 2 before I update original high-priority jobs. Approval required Update 11 jobs.',
    },
    ...overrides,
  }
}

test('transition oracle accepts matching backend, header, sidebar, document, and visible blocks', () => {
  const result = evaluateTransitionProbe(probe(), {
    sessionStatus: 'WAITING_APPROVAL',
    responseState: 'waiting_approval',
    pendingApprovalId: 'approval-2',
    revisionGreaterThan: 4,
    visibleBlockTypes: ['completed_step', 'approval_required'],
    hiddenBlockIds: ['approval:approval-1'],
    textIncludes: [/approval 2/i],
    approvalActionCount: 2,
  })

  assert.equal(result.ok, true)
  assert.deepEqual(result.violations, [])
})

test('transition oracle reports compact mismatches when visible UI is stale', () => {
  const result = evaluateTransitionProbe(probe({
    ui: {
      headerStatus: 'Waiting for approval',
      activeSidebarStatus: 'Waiting for approval',
      visibleBlockTypes: ['approval_required'],
      visibleBlockIds: ['approval:approval-1'],
      approvalActionLabels: ['Approve', 'Reject'],
      visibleBlocks: [
        { type: 'approval_required', id: 'approval:approval-1', text: 'Approval required Update 10 jobs.' },
      ],
      latestAssistantText: 'Waiting for approval 1 Approval required Update 10 jobs.',
      visibleText: 'Waiting for approval 1 Approval required Update 10 jobs.',
    },
  }), {
    sessionStatus: 'WAITING_APPROVAL',
    responseState: 'waiting_approval',
    pendingApprovalId: 'approval-2',
    visibleBlockIds: ['approval:approval-2'],
    hiddenBlockIds: ['approval:approval-1'],
    forbidWaitingApproval1: true,
  })

  assert.equal(result.ok, false)
  assert.match(result.violations.join('\n'), /visible block ids missing approval:approval-2/)
  assert.match(result.violations.join('\n'), /visible block ids still contained approval:approval-1/)
  assert.match(result.violations.join('\n'), /stale Waiting for approval 1/)

  const message = formatTransitionFailure({
    checkpoint: 'after approval 1',
    expected: { sessionStatus: 'WAITING_APPROVAL', responseState: 'waiting_approval' },
    result,
  })
  assert.match(message, /after approval 1/)
  assert.match(message, /approval:approval-1/)
  assert.equal(result.summary.diagnosis.classification, 'reducer_ordering_gap')
})

test('transition oracle forbids internal diagnostics and final stale approval text', () => {
  const result = evaluateTransitionProbe(probe({
    snapshot: {
      session: { status: 'COMPLETED' },
      phase: 'COMPLETED',
      pending_approval: null,
      response_document: {
        state: 'completed',
        revision: 12,
        blocks: [{ type: 'result_summary' }],
      },
    },
    ui: {
      headerStatus: 'Complete',
      activeSidebarStatus: 'Complete',
      visibleBlockTypes: ['result_summary', 'approval_required'],
      visibleBlockIds: ['result-summary:rd-1', 'approval:approval-2'],
      approvalActionLabels: ['Approve'],
      visibleBlocks: [
        { type: 'result_summary', id: 'result-summary:rd-1', text: 'Updated 21 jobs.' },
        { type: 'approval_required', id: 'approval:approval-2', text: 'Approval required' },
      ],
      latestAssistantText: 'Updated 21 jobs. Approval required. Reason: non_terminal_snapshot',
      visibleText: 'Updated 21 jobs. Approval required. Reason: non_terminal_snapshot',
    },
  }), {
    sessionStatus: 'COMPLETED',
    responseState: 'completed',
    pendingApprovalId: null,
    hiddenBlockTypes: ['approval_required'],
    approvalActionCount: 0,
  })

  assert.equal(result.ok, false)
  assert.match(result.violations.join('\n'), /visible block types still contained approval_required/)
  assert.match(result.violations.join('\n'), /internal non_terminal_snapshot reason/)
  assert.match(result.violations.join('\n'), /stale Approval required after completion/)
})

test('transition oracle summary keeps only high-signal fields', () => {
  const summary = summarizeTransitionProbe(probe())
  assert.equal(summary.kind, 'factory_agent_response_document_semantic_probe')
  assert.equal(summary.backend.sessionStatus, 'WAITING_APPROVAL')
  assert.equal(summary.backend.phase, 'WAITING_APPROVAL')
  assert.equal(summary.backend.pendingApprovalId, 'approval-2')
  assert.equal(summary.backend.responseDocumentState, 'waiting_approval')
  assert.equal(summary.backend.responseDocumentRevision, 8)
  assert.equal(summary.backend.responseDocumentCurrentStepId, 'approval-2')
  assert.deepEqual(summary.backend.responseBlockTypes, ['completed_step', 'approval_required'])
  assert.deepEqual(summary.backend.responseApprovalIds, ['approval-1', 'approval-2'])
  assert.deepEqual(summary.visible.visibleBlockTypes, ['completed_step', 'approval_required'])
  assert.equal(summary.artifactUse, 'Read this semantic probe first; screenshots and traces are supporting evidence.')
})
