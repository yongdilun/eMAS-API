import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { classifyFactoryAgentError, normalizeFactoryAgentError } from '../../../../services/factoryAgentErrors'
import { FACTORY_AGENT_STATUS, factoryAgentApi } from '../../../../services/factoryAgentApi'

const DEFAULT_USER_ID = import.meta.env?.VITE_FACTORY_AGENT_USER_ID || 'frontend-operator'
const ACTIVE_SESSION_KEY = 'factory_agent_active_session_id'
const MESSAGE_CACHE_PREFIX = 'factory_agent_messages:'
const SESSION_INDEX_KEY = 'factory_agent_session_index'
const SESSION_NAME_PREFIX = 'factory_agent_session_name:'
const SESSION_COUNTER_KEY = 'factory_agent_session_counter'
const hasStorage = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatTs(ts) {
  if (!ts) return nowTime()
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return nowTime()
  }
}

function messageCacheKey(sessionId) {
  return `${MESSAGE_CACHE_PREFIX}${sessionId || 'none'}`
}

function readCachedMessages(sessionId) {
  if (!hasStorage()) return []
  if (!sessionId) return []
  try {
    const raw = localStorage.getItem(messageCacheKey(sessionId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeCachedMessages(sessionId, messages) {
  if (!hasStorage()) return
  if (!sessionId) return
  try {
    localStorage.setItem(messageCacheKey(sessionId), JSON.stringify(messages.slice(-200)))
  } catch {
    // Ignore local storage write failures.
  }
}

function readSessionIndex() {
  if (!hasStorage()) return []
  try {
    const raw = localStorage.getItem(SESSION_INDEX_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeSessionIndex(ids) {
  if (!hasStorage()) return
  try {
    localStorage.setItem(SESSION_INDEX_KEY, JSON.stringify(Array.from(new Set(ids)).slice(0, 50)))
  } catch {
    // Ignore local storage write failures.
  }
}

function readSessionName(sessionId) {
  if (!hasStorage() || !sessionId) return null
  try {
    return localStorage.getItem(`${SESSION_NAME_PREFIX}${sessionId}`)
  } catch {
    return null
  }
}

function writeSessionName(sessionId, name) {
  if (!hasStorage() || !sessionId) return
  try {
    localStorage.setItem(`${SESSION_NAME_PREFIX}${sessionId}`, name)
  } catch {
    // Ignore local storage write failures.
  }
}

function nextSessionName() {
  if (!hasStorage()) return 'New chat'
  try {
    const current = Number(localStorage.getItem(SESSION_COUNTER_KEY) || '0')
    const next = Number.isFinite(current) ? current + 1 : 1
    localStorage.setItem(SESSION_COUNTER_KEY, String(next))
    return `Chat ${next}`
  } catch {
    return 'New chat'
  }
}

export function useFactoryAgentChat() {
  const [session, setSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [sessionList, setSessionList] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [error, setError] = useState(null)
  const [pendingApproval, setPendingApproval] = useState(null)
  const [approvalReason, setApprovalReason] = useState('')
  const [isDecidingApproval, setIsDecidingApproval] = useState(false)
  const [isPollingSession, setIsPollingSession] = useState(false)
  const [isPollingApprovals, setIsPollingApprovals] = useState(false)
  const [lastSyncedAt, setLastSyncedAt] = useState(null)

  const sessionPollTimerRef = useRef(null)
  const approvalPollTimerRef = useRef(null)
  const previousStatusRef = useRef(null)

  const upsertSessionSummary = useCallback((sessionId, patch = {}) => {
    if (!sessionId) return
    setSessionList((prev) => {
      const existing = prev.find((item) => item.session_id === sessionId)
      const fallbackName = readSessionName(sessionId) || 'New chat'
      const nextItem = {
        session_id: sessionId,
        name: patch.name || existing?.name || fallbackName,
        status: patch.status || existing?.status || FACTORY_AGENT_STATUS.IDLE,
        updated_at: patch.updated_at || new Date().toISOString(),
      }
      const without = prev.filter((item) => item.session_id !== sessionId)
      const next = [nextItem, ...without].slice(0, 50)
      writeSessionIndex(next.map((item) => item.session_id))
      return next
    })
  }, [])

  const appendMessage = useCallback((role, content, extra = {}) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
        timestamp: nowTime(),
        localOnly: true,
        ...extra,
      },
    ])
  }, [])

  const clearSessionPoll = useCallback(() => {
    if (sessionPollTimerRef.current) {
      clearInterval(sessionPollTimerRef.current)
      sessionPollTimerRef.current = null
    }
    setIsPollingSession(false)
  }, [])

  const clearApprovalPoll = useCallback(() => {
    if (approvalPollTimerRef.current) {
      clearInterval(approvalPollTimerRef.current)
      approvalPollTimerRef.current = null
    }
    setIsPollingApprovals(false)
  }, [])

  const clearAllPolling = useCallback(() => {
    clearSessionPoll()
    clearApprovalPoll()
  }, [clearApprovalPoll, clearSessionPoll])

  const syncArtifacts = useCallback(async (sessionId) => {
    if (!sessionId) return
    const [serverMessages, steps] = await Promise.all([
      factoryAgentApi.getMessages(sessionId),
      factoryAgentApi.getSteps(sessionId),
    ])

    const normalizedMessages = (Array.isArray(serverMessages) ? serverMessages : []).map((m) => ({
      id: m.message_id,
      role: m.role,
      content: m.content,
      timestamp: formatTs(m.created_at),
      step_id: m.step_id || null,
      tool_name: m.tool_name || null,
      sortAt: m.created_at || null,
    }))

    const toolResultStepIds = new Set(
      normalizedMessages
        .filter((m) => m.role === 'tool_result' && m.step_id)
        .map((m) => m.step_id)
    )

    const syntheticStepMessages = (Array.isArray(steps) ? steps : [])
      .filter((s) => ['DONE', 'FAILED', 'AMBIGUOUS'].includes(s.status))
      .filter((s) => !toolResultStepIds.has(s.step_id))
      .map((s) => {
        const content =
          s.result_summary ||
          (s.status === 'FAILED'
            ? `${s.tool_name} failed: ${s.last_error || 'Unknown error'}`
            : s.status === 'AMBIGUOUS'
              ? `${s.tool_name} returned ambiguous result. Manual verification needed.`
              : `${s.tool_name} completed.`)
        return {
          id: `step-${s.step_id}`,
          role: 'tool_result',
          content,
          timestamp: formatTs(s.completed_at || s.started_at),
          step_id: s.step_id,
          tool_name: s.tool_name,
          result: s.result || null,
          step_status: s.status,
          sortAt: s.completed_at || s.started_at || null,
        }
      })

    setMessages((prev) => {
      const localSystem = prev.filter((m) => m.localOnly === true && m.kind === 'system')
      const merged = [...localSystem, ...normalizedMessages, ...syntheticStepMessages]
      const byId = new Map()
      for (const item of merged) byId.set(item.id, item)
      return Array.from(byId.values()).sort((a, b) => {
        if (a.sortAt && b.sortAt) return String(a.sortAt).localeCompare(String(b.sortAt))
        return 0
      })
    })
  }, [])

  const loadPendingApproval = useCallback(async (sessionId) => {
    if (!sessionId) {
      setPendingApproval(null)
      return null
    }
    const all = await factoryAgentApi.listPendingApprovals()
    const own = Array.isArray(all) ? all.find((a) => a.session_id === sessionId && a.status === 'PENDING') : null
    setPendingApproval(own || null)
    return own || null
  }, [])

  const refreshSession = useCallback(async (sessionId) => {
    if (!sessionId) return null
    const snapshot = await factoryAgentApi.getSession(sessionId)
    setSession(snapshot)
    upsertSessionSummary(sessionId, { status: snapshot?.status, updated_at: new Date().toISOString() })
    await syncArtifacts(sessionId)
    setLastSyncedAt(new Date().toISOString())
    return snapshot
  }, [syncArtifacts, upsertSessionSummary])

  const safelyRefreshSession = useCallback(async (sessionId) => {
    try {
      return await refreshSession(sessionId)
    } catch (err) {
      const kind = classifyFactoryAgentError(err)
      if (kind === 'not_found') {
        if (hasStorage()) localStorage.removeItem(ACTIVE_SESSION_KEY)
        setSession(null)
        setPendingApproval(null)
        setMessages([])
      }
      throw err
    }
  }, [refreshSession])

  const pollSession = useCallback(async () => {
    if (!session?.session_id) return
    try {
      const fresh = await safelyRefreshSession(session.session_id)
      if (!fresh) return
      if (fresh.status !== FACTORY_AGENT_STATUS.WAITING_APPROVAL) {
        setPendingApproval(null)
      }
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to refresh session'))
    }
  }, [safelyRefreshSession, session?.session_id])

  const pollApprovals = useCallback(async () => {
    if (!session?.session_id || session.status !== FACTORY_AGENT_STATUS.WAITING_APPROVAL) return
    try {
      await loadPendingApproval(session.session_id)
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to refresh approvals'))
    }
  }, [loadPendingApproval, session?.session_id, session?.status])

  const sessionPollIntervalMs = useMemo(() => {
    if (!session?.status) return null
    if ([FACTORY_AGENT_STATUS.PLANNING, FACTORY_AGENT_STATUS.EXECUTING, FACTORY_AGENT_STATUS.WAITING_APPROVAL].includes(session.status)) {
      return 1500
    }
    if (session.status === FACTORY_AGENT_STATUS.BLOCKED) return 4000
    return null
  }, [session?.status])

  useEffect(() => {
    clearSessionPoll()
    if (!sessionPollIntervalMs || !session?.session_id) return
    setIsPollingSession(true)
    sessionPollTimerRef.current = setInterval(pollSession, sessionPollIntervalMs)
    return clearSessionPoll
  }, [clearSessionPoll, pollSession, session?.session_id, sessionPollIntervalMs])

  useEffect(() => {
    clearApprovalPoll()
    if (!session?.session_id || session?.status !== FACTORY_AGENT_STATUS.WAITING_APPROVAL) return
    setIsPollingApprovals(true)
    approvalPollTimerRef.current = setInterval(pollApprovals, 2000)
    return clearApprovalPoll
  }, [clearApprovalPoll, pollApprovals, session?.session_id, session?.status])

  useEffect(() => clearAllPolling, [clearAllPolling])

  useEffect(() => {
    if (!session?.session_id) return
    if (hasStorage()) localStorage.setItem(ACTIVE_SESSION_KEY, session.session_id)
    upsertSessionSummary(session.session_id, { status: session.status, updated_at: new Date().toISOString() })
  }, [session?.session_id, session?.status, upsertSessionSummary])

  useEffect(() => {
    if (!session?.session_id) return
    writeCachedMessages(session.session_id, messages)
    upsertSessionSummary(session.session_id, { updated_at: new Date().toISOString() })
  }, [messages, session?.session_id, upsertSessionSummary])

  useEffect(() => {
    const ids = readSessionIndex()
    const summaries = ids.map((sessionId) => ({
      session_id: sessionId,
      name: readSessionName(sessionId) || 'New chat',
      status: FACTORY_AGENT_STATUS.IDLE,
      updated_at: null,
    }))
    setSessionList(summaries)
  }, [])

  useEffect(() => {
    const previous = previousStatusRef.current
    const current = session?.status || null
    if (!current || !previous || previous === current) {
      previousStatusRef.current = current
      return
    }

    if (current === FACTORY_AGENT_STATUS.BLOCKED) {
      appendMessage('assistant', 'Execution is blocked. Review and retry or cancel.', { kind: 'system' })
    } else if (current === FACTORY_AGENT_STATUS.FAILED) {
      appendMessage('assistant', 'Session failed. Start a new session or retry.', { kind: 'system' })
    } else if (current === FACTORY_AGENT_STATUS.COMPLETED) {
      appendMessage('assistant', 'Execution completed successfully.', { kind: 'system' })
    } else if (current === FACTORY_AGENT_STATUS.WAITING_APPROVAL) {
      appendMessage('assistant', 'Waiting for approval to continue.', { kind: 'system' })
    }

    previousStatusRef.current = current
  }, [appendMessage, session?.status])

  useEffect(() => {
    const restore = async () => {
      if (!hasStorage()) return
      const savedId = localStorage.getItem(ACTIVE_SESSION_KEY)
      if (!savedId) return
      setLoading(true)
      setError(null)
      try {
        const restored = await safelyRefreshSession(savedId)
        if (!restored) return
        const cached = readCachedMessages(savedId)
        if (cached.length === 0) {
          const restoredName = readSessionName(savedId) || 'chat'
          setMessages([
            {
              id: `${Date.now()}-restore`,
              role: 'assistant',
              content: `Recovered ${restoredName}.`,
              timestamp: nowTime(),
              kind: 'system',
            },
          ])
        }
        if (restored.status === FACTORY_AGENT_STATUS.WAITING_APPROVAL) {
          await loadPendingApproval(savedId)
        }
      } catch (err) {
        setError(normalizeFactoryAgentError(err, 'Could not restore active session'))
      } finally {
        setLoading(false)
      }
    }

    restore()
  }, [loadPendingApproval, safelyRefreshSession])

  const startNewSession = useCallback(async () => {
    setLoading(true)
    setError(null)
    setPendingApproval(null)
    setMessages([])
    try {
      const s = await factoryAgentApi.createSession({ user_id: DEFAULT_USER_ID })
      const initialName = nextSessionName()
      writeSessionName(s.session_id, initialName)
      setSession(s)
      previousStatusRef.current = s?.status || null
      upsertSessionSummary(s.session_id, { name: initialName, status: s.status, updated_at: new Date().toISOString() })
      appendMessage('assistant', `Started ${initialName}.`, { kind: 'system' })
      return s
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to create session'))
      return null
    } finally {
      setLoading(false)
    }
  }, [appendMessage, upsertSessionSummary])

  const renameSession = useCallback((sessionId, name) => {
    const trimmed = (name || '').trim()
    if (!sessionId || !trimmed) return
    writeSessionName(sessionId, trimmed)
    setSessionList((prev) => prev.map((item) => (
      item.session_id === sessionId ? { ...item, name: trimmed } : item
    )))
  }, [])

  const switchSession = useCallback(async (sessionId) => {
    if (!sessionId) return
    setLoading(true)
    setError(null)
    try {
      const restored = await safelyRefreshSession(sessionId)
      if (!restored) return
      previousStatusRef.current = restored?.status || null
      if (restored.status === FACTORY_AGENT_STATUS.WAITING_APPROVAL) {
        await loadPendingApproval(sessionId)
      } else {
        setPendingApproval(null)
      }
      if (hasStorage()) localStorage.setItem(ACTIVE_SESSION_KEY, sessionId)
      upsertSessionSummary(sessionId, { status: restored.status, updated_at: new Date().toISOString() })
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Could not switch to selected session'))
    } finally {
      setLoading(false)
    }
  }, [loadPendingApproval, safelyRefreshSession, upsertSessionSummary])

  const executeWithRetry = useCallback(async (sessionId) => {
    try {
      return await factoryAgentApi.execute(sessionId, {})
    } catch (err) {
      if (err?.status === 409) {
        await safelyRefreshSession(sessionId)
        return factoryAgentApi.execute(sessionId, {})
      }
      throw err
    }
  }, [safelyRefreshSession])

  const runIntent = useCallback(async (sessionId, text) => {
    await factoryAgentApi.addMessage(sessionId, { role: 'user', content: text })
    await factoryAgentApi.createPlan(sessionId)
    appendMessage('assistant', 'Plan created. Starting execution.', { kind: 'system' })
    await executeWithRetry(sessionId)
    const latest = await safelyRefreshSession(sessionId)
    if (latest?.status === FACTORY_AGENT_STATUS.WAITING_APPROVAL) {
      await loadPendingApproval(sessionId)
    }
    return latest
  }, [appendMessage, executeWithRetry, loadPendingApproval, safelyRefreshSession])

  const retryFromCurrent = useCallback(async () => {
    if (!session?.session_id) return
    setError(null)
    try {
      await executeWithRetry(session.session_id)
      await safelyRefreshSession(session.session_id)
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to retry current session'))
    }
  }, [executeWithRetry, safelyRefreshSession, session?.session_id])

  const handleSend = useCallback(async (overrideText) => {
    const text = (overrideText ?? input).trim()
    if (!text || isSending) return

    appendMessage('user', text)
    setInput('')
    setError(null)
    setIsSending(true)

    try {
      let current = session

      if (!current || [FACTORY_AGENT_STATUS.FAILED, FACTORY_AGENT_STATUS.COMPLETED].includes(current.status)) {
        current = await startNewSession()
      }
      if (!current) return

      if ([FACTORY_AGENT_STATUS.EXECUTING, FACTORY_AGENT_STATUS.WAITING_APPROVAL, FACTORY_AGENT_STATUS.PLANNING].includes(current.status)) {
        await factoryAgentApi.addMessage(current.session_id, { role: 'user', content: text })
        appendMessage('assistant', 'Message received. It will be considered in the active run.', { kind: 'system' })
        await safelyRefreshSession(current.session_id)
      } else if (current.status === FACTORY_AGENT_STATUS.BLOCKED) {
        await factoryAgentApi.addMessage(current.session_id, { role: 'user', content: text })
        await factoryAgentApi.createPlan(current.session_id)
        await executeWithRetry(current.session_id)
        await safelyRefreshSession(current.session_id)
      } else {
        await runIntent(current.session_id, text)
      }
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to send request'))
      appendMessage('assistant', normalizeFactoryAgentError(err, 'I could not process that request.'))
    } finally {
      setIsSending(false)
    }
  }, [appendMessage, executeWithRetry, input, isSending, runIntent, safelyRefreshSession, session, startNewSession])

  const handleCancel = useCallback(async () => {
    if (!session?.session_id) return
    setIsCancelling(true)
    try {
      const next = await factoryAgentApi.cancelSession(session.session_id)
      setSession(next)
      setPendingApproval(null)
      appendMessage('assistant', 'Session cancelled. Completed steps were not rolled back.', { kind: 'system' })
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to cancel session'))
    } finally {
      setIsCancelling(false)
    }
  }, [appendMessage, session?.session_id])

  const decideApproval = useCallback(async (decision) => {
    if (!pendingApproval?.approval_id || isDecidingApproval) return
    setIsDecidingApproval(true)
    setError(null)
    try {
      if (decision === 'approve') {
        await factoryAgentApi.approve(pendingApproval.approval_id, { decided_by: DEFAULT_USER_ID })
        appendMessage('assistant', `Approved ${pendingApproval.tool_name}.`, { kind: 'system' })
        if (session?.session_id) {
          try {
            await executeWithRetry(session.session_id)
          } catch {
            // Backend event loop may already have resumed.
          }
        }
      } else {
        await factoryAgentApi.reject(pendingApproval.approval_id, {
          decided_by: DEFAULT_USER_ID,
          rejection_reason: approvalReason?.trim() || undefined,
        })
        appendMessage('assistant', `Rejected ${pendingApproval.tool_name}.`, { kind: 'system' })
      }
      setApprovalReason('')
      if (session?.session_id) {
        await safelyRefreshSession(session.session_id)
        await loadPendingApproval(session.session_id)
      }
    } catch (err) {
      setError(normalizeFactoryAgentError(err, 'Failed to submit approval decision'))
    } finally {
      setIsDecidingApproval(false)
    }
  }, [appendMessage, approvalReason, executeWithRetry, isDecidingApproval, loadPendingApproval, pendingApproval?.approval_id, pendingApproval?.tool_name, safelyRefreshSession, session?.session_id])

  const activeSessionName = useMemo(() => {
    if (!session?.session_id) return null
    const fromList = sessionList.find((item) => item.session_id === session.session_id)?.name
    return fromList || readSessionName(session.session_id) || 'New chat'
  }, [session?.session_id, sessionList])

  return {
    session,
    messages,
    sessionList,
    activeSessionName,
    input,
    setInput,
    loading,
    isSending,
    isCancelling,
    error,
    pendingApproval,
    approvalReason,
    setApprovalReason,
    isDecidingApproval,
    isPollingSession,
    isPollingApprovals,
    lastSyncedAt,
    handleSend,
    handleCancel,
    decideApproval,
    startNewSession,
    switchSession,
    renameSession,
    refreshSession: safelyRefreshSession,
    retryFromCurrent,
  }
}
