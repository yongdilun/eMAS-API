import fs from 'node:fs'
import path from 'node:path'

import { syntheticRuntimeEnv, redactSensitiveText } from './syntheticEnv.js'

const syntheticEnv = syntheticRuntimeEnv()
const results = []

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
}

function redactedJson(value) {
  return JSON.parse(redactSensitiveText(value))
}

export function classifySyntheticSignal(signal) {
  const alerts = []
  const owner = signal.owner || syntheticEnv.owner

  if (signal.timeout) {
    alerts.push({ code: 'synthetic_timeout', severity: 'critical', owner, message: 'Synthetic canary timed out before completion.' })
  }
  if (signal.backendUnavailable) {
    alerts.push({ code: 'backend_unavailable', severity: 'critical', owner, message: 'Factory Agent or Go API is unavailable.' })
  }
  if (signal.authFailure) {
    alerts.push({ code: 'auth_failure', severity: 'critical', owner, message: 'Synthetic auth token is expired, revoked, or rejected.' })
  }
  if (signal.providerOutage) {
    alerts.push({ code: 'provider_outage', severity: 'critical', owner, message: 'Model, RAG, or provider dependency failed.' })
  }
  if (signal.missingFinalAnswer) {
    alerts.push({ code: 'missing_final_answer', severity: 'critical', owner, message: 'Synthetic canary completed without a final answer.' })
  }
  if (signal.finalAnswerMs > syntheticEnv.latencyBudgetsMs.burnRateWarning) {
    alerts.push({ code: 'latency_burn_rate', severity: 'warning', owner, message: 'Synthetic latency is degraded before a hard outage.' })
  }

  return alerts
}

export function recordSyntheticResult(testInfo, result) {
  const record = redactedJson({
    kind: 'chatbot_synthetic_result',
    schema_version: 1,
    recorded_at: new Date().toISOString(),
    mode: syntheticEnv.mode,
    scenario: result.scenario || testInfo.title,
    status: result.status || (testInfo.status === testInfo.expectedStatus ? 'passed' : 'failed'),
    owner: result.owner || syntheticEnv.owner,
    checks: result.checks || [],
    metrics: result.metrics || {},
    alerts: result.alerts || [],
    artifact_retention: syntheticEnv.retention,
    notes: result.notes || [],
  })

  ensureDir(syntheticEnv.ndjsonPath)
  results.push(record)
  fs.appendFileSync(syntheticEnv.ndjsonPath, `${JSON.stringify(record)}\n`)
  fs.writeFileSync(
    syntheticEnv.resultPath,
    JSON.stringify(
      {
        kind: 'chatbot_synthetic_summary',
        schema_version: 1,
        updated_at: new Date().toISOString(),
        mode: syntheticEnv.mode,
        result_count: results.length,
        failed_count: results.filter((item) => item.status !== 'passed').length,
        alert_count: results.reduce((count, item) => count + item.alerts.length, 0),
        results,
      },
      null,
      2,
    ),
  )

  for (const alert of record.alerts) {
    fs.appendFileSync(syntheticEnv.alertPath, `${JSON.stringify({ ...alert, scenario: record.scenario, at: record.recorded_at })}\n`)
  }

  return record
}

export async function attachSyntheticResults(testInfo) {
  for (const filePath of [syntheticEnv.resultPath, syntheticEnv.ndjsonPath, syntheticEnv.alertPath]) {
    if (!fs.existsSync(filePath)) continue
    await testInfo.attach(path.basename(filePath), {
      body: redactSensitiveText(fs.readFileSync(filePath, 'utf8')),
      contentType: filePath.endsWith('.json') ? 'application/json' : 'application/x-ndjson',
    })
  }
}

