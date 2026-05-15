import http from 'node:http'
import { randomUUID } from 'node:crypto'
import {
  activeHappyPathSnapshot,
  buildHappyPathPlan,
  completedHappyPathSnapshot,
  createHappyPathSession,
  fixtureTime,
  machineStatusAnswer,
  machineStatusPrompt,
  sessionSummary,
} from '../fixtures/factoryAgentFixtures.js'

const args = new Map()
for (let i = 2; i < process.argv.length; i += 2) {
  args.set(process.argv[i], process.argv[i + 1])
}

const port = Number(args.get('--port') || process.env.PORT || 8015)
const sessions = new Map()

function now() {
  return new Date().toISOString()
}

function snapshot(session) {
  if (session.status === 'COMPLETED') return completedHappyPathSnapshot(session)
  if (session.status === 'PLANNING' || session.status === 'EXECUTING') return activeHappyPathSnapshot(session)
  return {
    session: sessionSummary(session),
    messages: session.messages,
    timeline: session.timeline || [],
    plan: session.plan || null,
    steps: session.steps || [],
    activity_steps: session.activity_steps || [],
    pending_approval: null,
    resume_hint: null,
  }
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function appendTimeline(session, event) {
  session.timeline.push({
    created_at: now(),
    ...event,
  })
  session.updated_at = now()
}

function writeSseHeaders(res) {
  res.writeHead(200, {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'Content-Type': 'text/event-stream',
  })
}

function sendSseEvent(res, event, data, id = 1) {
  res.write(`id: ${id}\n`)
  res.write(`event: ${event}\n`)
  res.write(`data: ${JSON.stringify(data)}\n\n`)
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    'Content-Type': 'application/json',
  })
  res.end(JSON.stringify(body))
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = ''
    req.on('data', (chunk) => {
      raw += chunk
    })
    req.on('end', () => {
      if (!raw) {
        resolve({})
        return
      }
      try {
        resolve(JSON.parse(raw))
      } catch (err) {
        reject(err)
      }
    })
  })
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`)

  if (req.method === 'OPTIONS') {
    sendJson(res, 204, {})
    return
  }

  if (req.method === 'GET' && url.pathname === '/health') {
    sendJson(res, 200, { ok: true })
    return
  }

  if (req.method === 'GET' && url.pathname === '/sessions') {
    sendJson(res, 200, Array.from(sessions.values()).map(sessionSummary))
    return
  }

  if (req.method === 'POST' && url.pathname === '/sessions') {
    const body = await readJson(req)
    const id = `pw-session-${randomUUID()}`
    const session = createHappyPathSession({
      sessionId: id,
      userId: body.user_id || 'playwright-user',
      name: body.name || 'Playwright session',
    })
    sessions.set(id, session)
    sendJson(res, 200, sessionSummary(session))
    return
  }

  const snapshotMatch = url.pathname.match(/^\/sessions\/([^/]+)\/snapshot$/)
  if (req.method === 'GET' && snapshotMatch) {
    const session = sessions.get(snapshotMatch[1])
    if (!session) {
      sendJson(res, 404, { detail: 'Session not found' })
      return
    }
    sendJson(res, 200, snapshot(session))
    return
  }

  const messagesMatch = url.pathname.match(/^\/sessions\/([^/]+)\/messages$/)
  if (req.method === 'POST' && messagesMatch) {
    const session = sessions.get(messagesMatch[1])
    if (!session) {
      sendJson(res, 404, { detail: 'Session not found' })
      return
    }
    const body = await readJson(req)
    const message = {
      id: `pw-message-${randomUUID()}`,
      role: body.role || 'user',
      content: body.content || '',
      mode: body.mode || 'normal',
      created_at: now(),
    }
    session.messages.push(message)
    session.status = 'PLANNING'
    appendTimeline(session, {
      event_id: 'pw-turn-machine-status',
      turn_id: 'pw-turn-machine-status',
      event_type: 'user_message',
      role: 'user',
      content: message.content || machineStatusPrompt,
      status: 'DONE',
      created_at: fixtureTime(1),
    })
    session.updated_at = now()
    sendJson(res, 200, message)
    return
  }

  const planMatch = url.pathname.match(/^\/sessions\/([^/]+)\/plans$/)
  if (req.method === 'POST' && planMatch) {
    const session = sessions.get(planMatch[1])
    if (!session) {
      sendJson(res, 404, { detail: 'Session not found' })
      return
    }
    session.status = 'EXECUTING'
    session.operation_id = 'pw-plan-machine-status'
    session.plan = buildHappyPathPlan(session)
    session.steps = [...session.plan.steps]
    appendTimeline(session, {
      event_id: 'pw-plan-created',
      turn_id: 'pw-turn-machine-status',
      event_type: 'plan_created',
      content: 'Checking machine status for M-CNC-01.',
      status: 'COMPLETED',
      operation_id: 'pw-plan-machine-status',
      details: {
        status: 'COMPLETED',
        plan_id: 'pw-plan-machine-status',
        plan_explanation: 'Checking machine status for M-CNC-01.',
      },
      created_at: fixtureTime(2),
    })
    session.updated_at = now()
    sendJson(res, 200, { status: 'EXECUTING', plan_id: 'pw-plan-machine-status' })
    return
  }

  const executeMatch = url.pathname.match(/^\/sessions\/([^/]+)\/execute$/)
  if (req.method === 'POST' && executeMatch) {
    const session = sessions.get(executeMatch[1])
    if (!session) {
      sendJson(res, 404, { detail: 'Session not found' })
      return
    }
    session.execute_count += 1
    session.status = 'EXECUTING'
    appendTimeline(session, {
      event_id: 'pw-execution-started',
      turn_id: 'pw-turn-machine-status',
      event_type: 'execution_started',
      content: 'Execution started.',
      status: 'IN_PROGRESS',
      operation_id: 'pw-plan-machine-status',
      created_at: fixtureTime(3),
    })
    await sleep(350)
    session.status = 'COMPLETED'
    session.steps = session.steps.map((step) => ({ ...step, status: 'DONE', updated_at: fixtureTime(4) }))
    appendTimeline(session, {
      event_id: 'pw-tool-result-machine-status',
      turn_id: 'pw-turn-machine-status',
      event_type: 'tool_result',
      step_id: 'pw-step-machine-status',
      tool_name: 'get_machine_status',
      content: machineStatusAnswer,
      status: 'DONE',
      operation_id: 'pw-plan-machine-status',
      details: {
        args: { machine_id: 'M-CNC-01' },
        result: {
          machine_id: 'M-CNC-01',
          status: 'RUNNING',
          utilization: 87,
          alarms: [],
          next_maintenance: 'Friday 14:00',
          _summary: machineStatusAnswer,
        },
      },
      created_at: fixtureTime(4),
    })
    appendTimeline(session, {
      event_id: 'pw-session-completed',
      turn_id: 'pw-turn-machine-status',
      event_type: 'session_completed',
      content: machineStatusAnswer,
      status: 'COMPLETED',
      operation_id: 'pw-plan-machine-status',
      details: { reason: 'happy_path_fixture' },
      created_at: fixtureTime(5),
    })
    sendJson(res, 200, { status: 'COMPLETED', session_id: session.session_id })
    return
  }

  const eventsMatch = url.pathname.match(/^\/sessions\/([^/]+)\/events$/)
  if (req.method === 'GET' && eventsMatch) {
    writeSseHeaders(res)
    sendSseEvent(res, 'notification', { type: 'hello', cursor: 1 })
    req.on('close', () => res.end())
    return
  }

  const activityEventsMatch = url.pathname.match(/^\/sessions\/([^/]+)\/events\/activity$/)
  if (req.method === 'GET' && activityEventsMatch) {
    writeSseHeaders(res)
    sendSseEvent(res, 'control', { type: 'STREAM_READY' })
    req.on('close', () => res.end())
    return
  }

  sendJson(res, 404, { detail: `No mock route for ${req.method} ${url.pathname}` })
})

server.listen(port, '127.0.0.1', () => {
  console.log(`Factory Agent mock listening on http://127.0.0.1:${port}`)
})

process.on('SIGTERM', () => server.close(() => process.exit(0)))
process.on('SIGINT', () => server.close(() => process.exit(0)))
