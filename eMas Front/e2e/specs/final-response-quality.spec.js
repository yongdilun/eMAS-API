import { expect, test } from '@playwright/test'
import { chatSelectors } from '../fixtures/selectors.js'
import { responseDocumentTrafficPrompt } from '../fixtures/factoryAgentFixtures.js'
import {
  forbiddenResponseDocumentText,
  responseDocumentCancelledRunPrompt,
  responseDocumentCascadePrompt,
  responseDocumentExpiredApprovalPrompt,
  responseDocumentLotoPrompt,
  responseDocumentNoResultsPrompt,
  responseDocumentPartialFailurePrompt,
  responseDocumentReadStatusPrompt,
  responseDocumentRejectedApprovalPrompt,
  responseDocumentReverseCascadePrompt,
  responseDocumentStaleApprovalPrompt,
  responseDocumentTimeoutPrompt,
} from '../support/responseDocumentScenarios.js'

async function openChat(page) {
  await page.goto('/')
  await page.getByRole('button', { name: chatSelectors.openAssistantButtonName }).click()
  await expect(page.getByRole('dialog', { name: chatSelectors.dialogName })).toBeVisible()
}

async function sendChatPrompt(page, prompt) {
  const composer = page.getByPlaceholder(chatSelectors.composerPlaceholder)
  const sendButton = page.getByRole('button', { name: chatSelectors.sendButtonName })
  await expect(composer).toBeEnabled()
  await composer.fill(prompt)
  await expect(sendButton).toBeEnabled()
  await sendButton.scrollIntoViewIfNeeded()
  await sendButton.click()
  await expect(page.getByText(prompt)).toBeVisible()
}

async function visibleText(page) {
  return page.locator('body').evaluate((body) => body.innerText)
}

async function expectForbiddenTextAbsent(page, patterns = forbiddenResponseDocumentText) {
  const text = await visibleText(page)
  for (const pattern of patterns) {
    expect(text).not.toMatch(pattern)
  }
}

async function expectDetailsClosed(locator) {
  await expect(locator).toBeVisible()
  expect(await locator.evaluate((node) => node.open)).toBe(false)
}

async function expectNoResponseDocumentOverflow(page) {
  const offenders = await page.locator('[data-response-document-root]').evaluateAll((roots) =>
    roots.flatMap((root) =>
      Array.from(root.querySelectorAll('[data-response-block-type], [data-response-document-root]'))
        .filter((node) => node.scrollWidth > node.clientWidth + 2)
        .map((node) => ({
          type: node.getAttribute('data-response-block-type') || 'root',
          text: (node.textContent || '').slice(0, 120),
          scrollWidth: node.scrollWidth,
          clientWidth: node.clientWidth,
        })),
    ),
  )
  expect(offenders).toEqual([])
}

async function expandActivity(page, label) {
  const activity = page.getByRole('button', { name: new RegExp(label, 'i') }).last()
  await expect(activity).toBeVisible()
  const expanded = await activity.getAttribute('aria-expanded')
  if (expanded !== 'true') await activity.click()
}

const exactAction = (name) => new RegExp(`^${name}$`)

async function decideApproval(page, action) {
  const label = action === 'approve' ? 'Approve' : 'Reject'
  const responsePromise = page.waitForResponse((response) =>
    response.url().includes('/approvals/') && response.url().endsWith(`/${action}`),
  )
  await page.getByRole('button', { name: exactAction(label) }).click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
}

async function runCascade(page, { prompt, finalMessage, firstStep, secondStep, firstRowsLabel, secondRowsLabel }) {
  await page.setViewportSize({ width: 390, height: 760 })
  await openChat(page)
  await sendChatPrompt(page, prompt)

  await expect(page.getByText('Understood request').first()).toBeVisible()
  await expect(page.getByText(firstRowsLabel).first()).toBeVisible()
  await expect(page.getByText('Waiting for approval 1').first()).toBeVisible()
  const firstApprovalCard = page.locator('[data-response-block-type="approval_required"]').filter({ hasText: firstStep }).last()
  await expect(firstApprovalCard).toBeVisible()
  await expect(firstApprovalCard).toContainText(firstStep)
  await expect(firstApprovalCard).toContainText(/JOB-SEED-00[12]/)
  await expect(firstApprovalCard).toContainText(/\+\d+ more/)
  await expect(page.getByText('Run complete')).toHaveCount(0)
  await expect(page.getByText(finalMessage)).toHaveCount(0)
  await expectNoResponseDocumentOverflow(page)

  const firstDetails = page.locator('details').filter({ hasText: /Affected records \(\d+\)/ }).first()
  await expectDetailsClosed(firstDetails)
  await firstDetails.locator('summary').click()
  expect(await firstDetails.evaluate((node) => node.open)).toBe(true)
  await firstDetails.locator('summary').click()
  expect(await firstDetails.evaluate((node) => node.open)).toBe(false)
  await page.waitForTimeout(3300)
  await expectDetailsClosed(firstDetails)

  await page.setViewportSize({ width: 1280, height: 900 })
  await decideApproval(page, 'approve')
  await expect(page.getByText('Waiting for approval 2').first()).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText(secondRowsLabel).first()).toBeVisible()
  await expect(page.getByText(new RegExp(firstStep.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/^Update/, 'Updated'))).first()).toBeVisible()
  const secondApprovalCard = page.locator('[data-response-block-type="approval_required"]').filter({ hasText: secondStep }).last()
  await expect(secondApprovalCard).toBeVisible()
  await expect(secondApprovalCard).toContainText(secondStep)
  await expect(page.getByText('Run complete')).toHaveCount(0)
  await expect(page.getByText(finalMessage)).toHaveCount(0)

  await decideApproval(page, 'approve')
  await expect(page.getByText(finalMessage).first()).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('Run complete').first()).toBeVisible()
  await expect(page.getByText('Step 1').first()).toBeVisible()
  await expect(page.getByText('Step 2').first()).toBeVisible()
  await expect(page.getByText(/original .*priority jobs changed/i).first()).toBeVisible()
  await expect(page.getByText('Approval required')).toHaveCount(0)
  await expect(page.getByText(/Waiting for approval \d/)).toHaveCount(0)
  await expectForbiddenTextAbsent(page, [
    /All requested changes completed/i,
    /Approved request to change record/i,
    /Response document invalid/i,
    /Traceback/i,
    /super-secret/i,
  ])
}

test.describe('Final response quality response_document gate', () => {
  test('two-approval cascade keeps compact pending state and final aggregate truth', async ({ page }) => {
    await runCascade(page, {
      prompt: responseDocumentCascadePrompt,
      finalMessage: 'Updated 21 jobs across 2 approved steps.',
      firstStep: 'Update 10 jobs from medium to high',
      secondStep: 'Update 11 jobs from high to low',
      firstRowsLabel: 'Found 10 original medium-priority jobs',
      secondRowsLabel: 'Found 11 original high-priority jobs',
    })
  })

  test('reverse two-approval cascade converges to final aggregate truth', async ({ page }) => {
    await runCascade(page, {
      prompt: responseDocumentReverseCascadePrompt,
      finalMessage: 'Updated 16 jobs across 2 approved steps.',
      firstStep: 'Update 11 jobs from high to low',
      secondStep: 'Update 5 jobs from low to medium',
      firstRowsLabel: 'Found 11 original high-priority jobs',
      secondRowsLabel: 'Found 5 original low-priority jobs',
    })
  })

  test('read-only machine status and RAG source blocks render from typed documents', async ({ page }) => {
    await openChat(page)
    await sendChatPrompt(page, responseDocumentReadStatusPrompt)
    await expect(page.getByText('Machine M-CNC-01 is running normally at 87% utilization with no active alarms.').first()).toBeVisible()
    await expandActivity(page, 'Run complete')
    await expect(page.getByText('Read machine status').first()).toBeVisible()
    await expect(page.getByText('Run complete').first()).toBeVisible()
    await expect(page.locator('details').filter({ hasText: 'Machine status (1)' }).first()).toBeVisible()
    await expect(page.getByText('Approval required')).toHaveCount(0)

    await sendChatPrompt(page, responseDocumentLotoPrompt)
    await expect(page.getByText(/Use the M-CNC-01 lockout\/tagout procedure/i).first()).toBeVisible()
    await expandActivity(page, 'Run complete')
    await expect(page.getByText('Prepared sourced answer').first()).toBeVisible()
    await expect(page.getByText('Knowledge sources').first()).toBeVisible()
    await expect(page.getByText('M-CNC-01 Lockout/Tagout Procedure').first()).toBeVisible()
    await expect(page.getByText('LOTO-M-CNC-01').first()).toBeVisible()
    await expectForbiddenTextAbsent(page)
  })

  test('diagnostic documents cover no-result, partial failure, timeout, expired, and stale approvals', async ({ page }) => {
    await openChat(page)
    const cases = [
      [responseDocumentNoResultsPrompt, /No matching jobs were found/i, 'No results'],
      [responseDocumentPartialFailurePrompt, /Some rows were updated, but other rows failed/i, 'Partial failure'],
      [responseDocumentTimeoutPrompt, /planner timed out while preparing the next step/i, 'Run interrupted'],
      [responseDocumentExpiredApprovalPrompt, /approval expired/i, 'Approval expired'],
      [responseDocumentStaleApprovalPrompt, /approval is stale/i, 'Approval is stale'],
    ]

    for (const [prompt, messagePattern, title] of cases) {
      await sendChatPrompt(page, prompt)
      await expect(page.getByText(messagePattern).first()).toBeVisible()
      await expect(page.getByText(title).first()).toBeVisible()
      await expect(page.getByText('Technical details').last()).toBeVisible()
      const technical = page.locator('details').filter({ hasText: 'Technical details' }).last()
      await expectDetailsClosed(technical)
      await expect(page.getByText('Approval required')).toHaveCount(0)
      await expect(page.getByRole('button', { name: exactAction('Approve') })).toHaveCount(0)
      await expectForbiddenTextAbsent(page)
    }
  })

  test('rejected approval closes actions while preserving completed prior step', async ({ page }) => {
    await openChat(page)
    await sendChatPrompt(page, responseDocumentRejectedApprovalPrompt)
    await expect(page.getByText('Completed step').first()).toBeVisible()
    await expect(page.getByText('Update 11 jobs from high to low').first()).toBeVisible()
    await expect(page.getByRole('button', { name: exactAction('Reject') })).toBeVisible()

    await page.getByRole('button', { name: exactAction('Reject') }).click()
    await expect(page.getByText('Approval rejected').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('The approval was rejected, so I did not apply that pending change.').first()).toBeVisible()
    await expect(page.getByText('Updated 10 jobs from medium to high.').first()).toBeVisible()
    await expect(page.getByRole('button', { name: exactAction('Approve') })).toHaveCount(0)
    await expect(page.getByRole('button', { name: exactAction('Reject') })).toHaveCount(0)
    await expect(page.getByText('Run complete')).toHaveCount(0)
    await expectForbiddenTextAbsent(page)
  })

  test('cancelled run renders typed cancelled diagnostic with no stale pending state', async ({ page }) => {
    await openChat(page)
    await sendChatPrompt(page, responseDocumentCancelledRunPrompt)
    await expect(page.getByText('I am checking records and can still be cancelled.').first()).toBeVisible()
    await expect(page.getByText('Checking records').first()).toBeVisible()
    await page.getByRole('button', { name: 'Cancel current run' }).click()

    await expect(page.getByText('Run cancelled').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('The run was cancelled. I stopped work and did not continue pending actions.').first()).toBeVisible()
    await expect(page.getByText('Approval required')).toHaveCount(0)
    await expect(page.getByText('Run complete')).toHaveCount(0)
    await expectForbiddenTextAbsent(page)
  })

  test('busy traffic event storm converges on final response without stale blocks', async ({ page }) => {
    await openChat(page)
    await sendChatPrompt(page, responseDocumentTrafficPrompt)

    await expect(page.getByText('Updated 21 jobs across 2 approved steps.').first()).toBeVisible({ timeout: 10_000 })
    await page.waitForTimeout(900)
    await expect(page.getByText('Updated 21 jobs across 2 approved steps.').first()).toBeVisible()
    await expect(page.getByText('Stale failure: database unavailable.')).toHaveCount(0)
    await expect(page.getByText('Response document invalid')).toHaveCount(0)
    await expect(page.getByText('Approval required')).toHaveCount(0)
    await expect(page.getByText('Waiting for approval 2')).toHaveCount(0)
  })
})
