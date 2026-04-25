export const getReadableAction = (toolName) => {
  const raw = String(toolName || '').trim()
  const lower = raw.toLowerCase()
  if (!lower) return 'Processing'
  if (lower.startsWith('get')) return 'Inspecting'
  if (lower.startsWith('list')) return 'Inspecting'
  if (lower.startsWith('post') || lower.startsWith('create')) return 'Creating'
  if (lower.startsWith('put') || lower.startsWith('patch') || lower.startsWith('update')) return 'Updating'
  if (lower.startsWith('delete') || lower.startsWith('remove')) return 'Deleting'
  return 'Processing'
}

const safeStr = (v) => (v == null ? '' : String(v))

function pickLatestTurnIdByTime(userEvents, atIso) {
  if (!userEvents.length) return null
  if (!atIso) return userEvents[userEvents.length - 1].turn_id || userEvents[userEvents.length - 1].event_id || null
  const at = new Date(atIso).getTime()
  if (!Number.isFinite(at)) return userEvents[userEvents.length - 1].turn_id || userEvents[userEvents.length - 1].event_id || null
  let selected = null
  for (const e of userEvents) {
    const t = new Date(e.created_at).getTime()
    if (!Number.isFinite(t)) continue
    if (t <= at) selected = e
    else break
  }
  const fallback = selected || userEvents[userEvents.length - 1]
  return fallback.turn_id || fallback.event_id || null
}

export function assembleFactoryAgentTurns(timeline = []) {
  const events = Array.isArray(timeline) ? timeline : []
  const userEvents = events.filter((e) => e?.event_type === 'user_message')

  const turnsById = new Map()
  const toolBlocksByKey = new Map()
  const getOrCreateTurn = (turnId, createdAt) => {
    const key = turnId || `turn:${createdAt || 'unknown'}:${Math.random().toString(36).slice(2, 8)}`
    const existing = turnsById.get(key)
    if (existing) return existing
    const next = {
      id: key,
      created_at: createdAt || null,
      user: null,
      thinking: [],
      tools: [],
      approvals: [],
      status: [],
      terminal: null,
      debug: [],
    }
    turnsById.set(key, next)
    return next
  }

  const upsertToolBlock = (turn, e, patch) => {
    const stepId = e.step_id || e.stepId || (e.details && e.details.step_id) || null
    const key = `${turn.id}:${stepId || e.event_id || e.id}`
    const existing = toolBlocksByKey.get(key) || null
    if (existing) {
      Object.assign(existing, patch)
      return
    }
    const next = { ...patch }
    turn.tools.push(next)
    toolBlocksByKey.set(key, next)
  }

  for (const e of events) {
    if (!e) continue
    const turnId =
      e.turn_id ||
      (e.event_type === 'user_message'
        ? (e.event_id || e.id)
        : pickLatestTurnIdByTime(userEvents, e.created_at))
    const turn = getOrCreateTurn(turnId, e.created_at)

    if (e.event_type === 'user_message') {
      turn.user = {
        id: e.event_id || e.id,
        content: e.content,
        created_at: e.created_at,
      }
      continue
    }

    if (e.event_type === 'plan_created') {
      turn.thinking.push({
        id: e.event_id || e.id,
        content: e.content,
        created_at: e.created_at,
        details: e.details || null,
      })
      continue
    }

    if (e.event_type === 'tool_started') {
      upsertToolBlock(turn, e, {
        id: e.step_id || e.event_id || e.id,
        step_id: e.step_id || null,
        tool_name: e.tool_name,
        action: getReadableAction(e.tool_name),
        status: e.status || 'IN_PROGRESS',
        content: e.content,
        created_at: e.created_at,
        details: e.details || null,
      })
      continue
    }

    if (e.event_type === 'tool_result') {
      upsertToolBlock(turn, e, {
        id: e.step_id || e.event_id || e.id,
        step_id: e.step_id || null,
        tool_name: e.tool_name,
        action: getReadableAction(e.tool_name),
        status: e.status || null,
        content: e.content,
        created_at: e.created_at,
        details: e.details || null,
      })
      continue
    }

    if (e.event_type === 'approval_required' || e.event_type === 'approval_decided') {
      turn.approvals.push({
        id: e.event_id || e.id,
        event_type: e.event_type,
        tool_name: e.tool_name,
        approval_id: e.approval_id,
        step_id: e.step_id,
        status: e.status || null,
        content: e.content,
        created_at: e.created_at,
        details: e.details || null,
      })
      continue
    }

    if (['execution_started', 'replan_requested', 'session_blocked', 'session_failed', 'session_completed'].includes(e.event_type)) {
      const item = {
        id: e.event_id || e.id,
        event_type: e.event_type,
        content: e.content,
        created_at: e.created_at,
        status: e.status || null,
        details: e.details || null,
      }
      turn.status.push(item)
      if (e.event_type === 'session_blocked' || e.event_type === 'session_failed' || e.event_type === 'session_completed') {
        turn.terminal = item
      }
      continue
    }

    turn.debug.push(e)
  }

  const turns = Array.from(turnsById.values())
  turns.sort((a, b) => safeStr(a.user?.created_at || a.created_at).localeCompare(safeStr(b.user?.created_at || b.created_at)))

  return turns
}

export function computeFactoryAgentTurnSummary(turn) {
  if (!turn) return 'Working...'

  const toTs = (value) => {
    const ts = Date.parse(value || '')
    return Number.isFinite(ts) ? ts : -Infinity
  }

  const lastApproval = Array.isArray(turn.approvals) ? turn.approvals[turn.approvals.length - 1] : null
  const lastTool = Array.isArray(turn.tools) ? turn.tools[turn.tools.length - 1] : null
  const terminal = turn.terminal || null
  const approvalTs = toTs(lastApproval?.created_at)
  const latestProgressTs = Math.max(toTs(lastTool?.created_at), toTs(terminal?.created_at))
  const waitingOnApproval = latestProgressTs <= approvalTs

  if (lastApproval?.event_type === 'approval_required' && waitingOnApproval) {
    return lastApproval.content || 'Waiting for approval.'
  }
  if (lastApproval?.event_type === 'approval_decided' && waitingOnApproval) {
    return lastApproval.content || (String(lastApproval.status || '').toUpperCase() === 'REJECTED' ? 'Approval rejected.' : 'Approval decided.')
  }

  if (terminal?.event_type === 'session_blocked' || terminal?.event_type === 'session_failed') {
    return terminal.content || 'Execution stopped.'
  }
  if (terminal?.event_type === 'session_completed') {
    // Prefer the last tool result when completion is a generic status line.
    const isGenericComplete = String(terminal.content || '').toLowerCase().includes('execution completed successfully')
    if (isGenericComplete) {
      const toolLines = (Array.isArray(turn.tools) ? turn.tools : [])
        .map((t) => (t?.content ? String(t.content).trim() : ''))
        .filter(Boolean)
      const deduped = toolLines.filter((line, idx) => toolLines.indexOf(line) === idx)
      if (deduped.length >= 2) return deduped.join('\n')
      if (lastTool?.content) return lastTool.content
    }
    return terminal.content || 'Execution completed.'
  }

  if (lastTool?.content) return lastTool.content

  const lastPlan = Array.isArray(turn.thinking) ? turn.thinking[turn.thinking.length - 1] : null
  if (lastPlan?.details?.status === 'COMPLETED' && lastPlan?.content) return lastPlan.content
  if (lastPlan?.content) return 'Working...'

  return 'Working...'
}

export function assembleLegacyTurns(messages = []) {
  const rows = Array.isArray(messages) ? messages : []
  const turns = []
  let current = null

  const startTurn = (userMsg) => {
    current = {
      id: userMsg?.turnId || userMsg?.id || `turn:${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      user: userMsg || null,
      assistants: [],
    }
    turns.push(current)
  }

  for (const m of rows) {
    if (!m) continue
    if (m.role === 'user') {
      startTurn(m)
      continue
    }
    if (!current) startTurn(null)
    current.assistants.push(m)
  }

  return turns
}

export function mergeLegacyAssistantTurnContent(turn) {
  const assistants = Array.isArray(turn?.assistants) ? turn.assistants : []
  const primary = assistants.find((a) => a?.content) || assistants[0] || null
  if (!primary) return { content: '', blocks: [] }

  const blocks = []

  // Thinking (intent/confidence/entities/BDI) is hidden by default; surfaced as a collapsible.
  const thinkingPayload = {
    intent: primary.intent,
    confidence: primary.confidence,
    ambiguous: primary.ambiguous,
    clarifications: primary.clarifications,
    bdi_result: primary.bdi_result,
  }
  blocks.push({ type: 'thinking', title: 'Thinking', payload: thinkingPayload })

  const toolBlocks = []
  for (const a of assistants) {
    const calls = a?.suggested_calls || a?.suggestedCalls || []
    for (const call of calls) {
      toolBlocks.push({
        type: 'tool_call',
        title: call?.purpose || `${call?.method || 'GET'} ${call?.path || ''}`,
        tool_name: call?.path,
        action: getReadableAction(call?.method || ''),
        status: call?.requires_approval ? 'PENDING_APPROVAL' : 'SUGGESTED',
        payload: call,
      })
    }

    const execBlocks = Array.isArray(a?.tool_blocks) ? a.tool_blocks : []
    for (const b of execBlocks) {
      if (b?.kind !== 'tool') continue
      toolBlocks.push({
        type: 'tool_call',
        title: b?.call?.purpose || `${b?.call?.method || 'GET'} ${b?.call?.path || ''}`,
        tool_name: b?.call?.path,
        action: getReadableAction(b?.call?.method || ''),
        status: b?.status || 'DONE',
        payload: { call: b.call, status: b.status, result: b.result, error: b.error },
      })
    }
  }
  if (toolBlocks.length) blocks.push(...toolBlocks)

  return { content: primary.content || '', blocks }
}
