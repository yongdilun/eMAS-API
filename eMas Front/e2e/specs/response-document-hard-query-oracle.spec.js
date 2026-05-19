import { expect, test } from '@playwright/test'

import { hardQueryScenarios } from '../support/hardQueryScenarios.js'

test('response_document hard query oracle catalog includes HQ-01 HQ-05 HQ-3S-01 semantic contracts', () => {
  expect(hardQueryScenarios.map((scenario) => scenario.id)).toEqual(['HQ-01', 'HQ-05', 'HQ-3S-01'])

  for (const scenario of hardQueryScenarios) {
    expect(scenario.prompt, `${scenario.id} prompt`).toBeTruthy()
    expect(scenario.expected.sessionStatus).toBe('COMPLETED')
    expect(scenario.expected.responseState).toBe('completed')
    expect(scenario.expected.stepSequence.length).toBeGreaterThan(0)
    expect(scenario.expected.visibleSemanticBlocks.length).toBeGreaterThan(0)
    expect(scenario.expected.approvalCount).toBe(0)
    expect(scenario.expected.noMutation).toBe(true)
  }

  const statusOnly = hardQueryScenarios.find((scenario) => scenario.id === 'HQ-01')
  expect(statusOnly.expected.responseDocument.contracts).toContain('entity_status_v1')
  expect(statusOnly.expected.visibleSemanticBlocks[0].requestedFields).toEqual(['machine_id', 'status'])
  expect(statusOnly.expected.visibleSemanticBlocks[0].displayMode).toBe('compact_status_card')

  const lowPriority = hardQueryScenarios.find((scenario) => scenario.id === 'HQ-05')
  expect(lowPriority.expected.stepSequence[0].args).toMatchObject({
    priority: 'low',
    sort_by: 'deadline',
    sort_dir: 'asc',
    limit: 3,
  })
  expect(lowPriority.expected.visibleSemanticBlocks[0].tableColumnKeys).toEqual(['job_id', 'deadline'])

  const ordered = hardQueryScenarios.find((scenario) => scenario.id === 'HQ-3S-01')
  expect(ordered.expected.stepSequence.map((step) => step.toolName)).toEqual([
    'get__machines_{id}',
    'get__jobs_{id}',
    'get__jobs',
  ])
  expect(ordered.expected.responseDocument.minReadRunSteps).toBeGreaterThanOrEqual(3)
})
