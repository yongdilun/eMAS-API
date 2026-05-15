/* eslint-env node */
/**
 * Factory-agent smoke script.
 *
 * Run:
 *   node scripts/factory-agent-smoke.js
 *
 * Optional env:
 *   FACTORY_AGENT_BASE_URL=http://127.0.0.1:8000
 *   FACTORY_AGENT_BEARER_TOKEN=...
 *   FACTORY_AGENT_USER_ID=frontend-smoke
 *   FACTORY_AGENT_INTENT="list machines"
 *   FACTORY_AGENT_APPROVAL_DECISION=approve|reject
 */

const BASE = (process.env.FACTORY_AGENT_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const TOKEN = process.env.FACTORY_AGENT_BEARER_TOKEN || ''
const USER_ID = process.env.FACTORY_AGENT_USER_ID || 'frontend-smoke'
const INTENT = process.env.FACTORY_AGENT_INTENT || 'list machines'
const APPROVAL_DECISION = (process.env.FACTORY_AGENT_APPROVAL_DECISION || 'reject').toLowerCase()

function h() {
  const headers = { 'Content-Type': 'application/json' }
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`
  return headers
}

async function req(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: h(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let json = null
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    json = text
  }
  if (!res.ok) {
    const detail = typeof json === 'object' && json ? JSON.stringify(json) : String(json)
    throw new Error(`[${res.status}] ${method} ${path} -> ${detail}`)
  }
  return json
}

async function waitForStatus(sessionId, accepted, timeoutMs = 90000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const s = await req('GET', `/sessions/${sessionId}`)
    if (accepted.includes(s.status)) return s
    await new Promise((r) => setTimeout(r, 1500))
  }
  throw new Error(`Timed out waiting for status in [${accepted.join(', ')}]`)
}

async function runMainFlow() {
  const session = await req('POST', '/sessions', { user_id: USER_ID })
  console.log(`session created: ${session.session_id}`)

  await req('POST', `/sessions/${session.session_id}/messages`, { role: 'user', content: INTENT })
  console.log('message added')

  await req('POST', `/sessions/${session.session_id}/plans`, {})
  console.log('plan created')

  await req('POST', `/sessions/${session.session_id}/execute`, {})
  console.log('execute started')

  let current = await waitForStatus(
    session.session_id,
    ['WAITING_APPROVAL', 'EXECUTING', 'COMPLETED', 'FAILED', 'BLOCKED'],
    90000
  )
  console.log(`status reached: ${current.status}`)

  if (current.status === 'WAITING_APPROVAL') {
    const approvals = await req('GET', '/approvals/pending')
    const own = (approvals || []).find((a) => a.session_id === session.session_id && a.status === 'PENDING')
    if (!own) throw new Error('Expected pending approval but none found')
    console.log(`approval found: ${own.approval_id} (${own.tool_name})`)

    if (APPROVAL_DECISION === 'approve') {
      await req('POST', `/approvals/${own.approval_id}/approve`, { decided_by: USER_ID })
      console.log('approval approved')
    } else {
      await req('POST', `/approvals/${own.approval_id}/reject`, {
        decided_by: USER_ID,
        rejection_reason: 'smoke-test reject',
      })
      console.log('approval rejected')
    }

    current = await waitForStatus(session.session_id, ['IDLE', 'EXECUTING', 'COMPLETED', 'FAILED', 'BLOCKED'], 90000)
    console.log(`post-approval status: ${current.status}`)
  }

  console.log('main flow finished')
  return session.session_id
}

async function runCancelFlow() {
  const session = await req('POST', '/sessions', { user_id: USER_ID })
  await req('POST', `/sessions/${session.session_id}/messages`, {
    role: 'user',
    content: 'Show status for machine M-CNC-01',
  })
  await req('POST', `/sessions/${session.session_id}/cancel`, {})
  const final = await req('GET', `/sessions/${session.session_id}`)
  if (final.status !== 'IDLE') {
    throw new Error(`Expected cancelled session to be IDLE, got ${final.status}`)
  }
  console.log(`cancel flow status: ${final.status}`)
}

async function main() {
  console.log('factory-agent smoke start')
  console.log(`base=${BASE} user=${USER_ID} approval=${APPROVAL_DECISION}`)
  await runMainFlow()
  await runCancelFlow()
  console.log('factory-agent smoke passed')
}

main().catch((err) => {
  console.error('factory-agent smoke failed')
  console.error(err)
  process.exit(1)
})
