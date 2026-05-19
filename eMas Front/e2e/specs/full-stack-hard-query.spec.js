import { test } from '../support/seededArtifacts.js'
import {
  openChat,
  pendingApprovalsForPage,
  sendPrompt,
  snapshotForPage,
} from '../support/fullStackScenarios.js'
import { hardQueryScenarios } from '../support/hardQueryScenarios.js'
import { expectHardQueryScenario } from '../support/hardQueryOracle.js'

test.describe('Hard query oracle harness @prompt-regression @hard-query', () => {
  for (const scenario of hardQueryScenarios) {
    test(`${scenario.id} hard query proves typed oracle contract`, async ({ page }, testInfo) => {
      await openChat(page)
      await sendPrompt(page, scenario.prompt)
      await expectHardQueryScenario(page, scenario, {
        snapshotForPage,
        pendingApprovalsForPage,
        testInfo,
      })
    })
  }
})
