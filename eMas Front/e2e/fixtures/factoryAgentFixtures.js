export const machineStatusPrompt = 'Show status for machine M-CNC-01'

export const machineStatusAnswer =
  'Machine M-CNC-01 is running normally at 87% utilization. No active alarms are reported, and the next preventive maintenance window is scheduled for Friday at 14:00.'

const baseTime = Date.parse('2026-05-16T04:00:00.000Z')

export function fixtureTime(offsetSeconds = 0) {
  return new Date(baseTime + offsetSeconds * 1000).toISOString()
}

export function createHappyPathSession({ sessionId, userId, name }) {
  const createdAt = fixtureTime()
  return {
    session_id: sessionId,
    user_id: userId || 'frontend-operator',
    name: name || 'Playwright session',
    status: 'IDLE',
    created_at: createdAt,
    updated_at: createdAt,
    operation_id: null,
    messages: [],
    timeline: [],
    plan: null,
    steps: [],
    activity_steps: [],
    pending_approval: null,
    execute_count: 0,
  }
}

export function buildHappyPathPlan(session) {
  return {
    plan_id: 'pw-plan-machine-status',
    session_id: session.session_id,
    status: 'EXECUTING',
    objective: 'Review machine status for M-CNC-01',
    created_at: fixtureTime(2),
    updated_at: fixtureTime(2),
    steps: [
      {
        id: 'pw-step-machine-status',
        plan_id: 'pw-plan-machine-status',
        tool_name: 'get_machine_status',
        status: 'IN_PROGRESS',
        created_at: fixtureTime(3),
      },
    ],
  }
}

export function activeHappyPathSnapshot(session) {
  return {
    session: sessionSummary(session),
    messages: session.messages,
    timeline: [...session.timeline],
    plan: session.plan,
    steps: session.steps,
    activity_steps: [
      {
        id: 'pw-activity-understanding',
        timestamp: Date.parse(fixtureTime(1)) / 1000,
        group: 'planning',
        label: 'Understanding your request',
        detail: 'Reviewing machine M-CNC-01 and recent context',
        state: 'running',
      },
    ],
    pending_approval: null,
    resume_hint: null,
  }
}

export function completedHappyPathSnapshot(session) {
  return {
    session: sessionSummary(session),
    messages: session.messages,
    timeline: [...session.timeline],
    plan: session.plan,
    steps: session.steps,
    activity_steps: [
      {
        id: 'pw-activity-understanding',
        timestamp: Date.parse(fixtureTime(1)) / 1000,
        group: 'planning',
        label: 'Understanding your request',
        detail: 'Reviewing machine M-CNC-01 and recent context',
        state: 'success',
      },
      {
        id: 'pw-activity-checking',
        timestamp: Date.parse(fixtureTime(4)) / 1000,
        group: 'research',
        label: 'Gathering information',
        detail: 'Checking machine records',
        state: 'success',
      },
      {
        id: 'pw-activity-complete',
        timestamp: Date.parse(fixtureTime(5)) / 1000,
        group: 'response',
        label: 'Run complete',
        detail: 'All steps finished. See the thread below.',
        state: 'complete',
      },
    ],
    pending_approval: null,
    resume_hint: null,
  }
}

export function sessionSummary(session) {
  return {
    session_id: session.session_id,
    user_id: session.user_id,
    name: session.name,
    status: session.status,
    created_at: session.created_at,
    updated_at: session.updated_at,
    operation_id: session.operation_id || session.plan?.plan_id || null,
  }
}
