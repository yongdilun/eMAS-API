import logger from './logger'
import { normalizeFactoryAgentError } from './factoryAgentErrors'

const FACTORY_AGENT_BASE_URL = (
  import.meta.env?.VITE_FACTORY_AGENT_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/+$/, '')

const STATIC_BEARER = import.meta.env?.VITE_FACTORY_AGENT_BEARER_TOKEN || ''

function buildUrl(path) {
  if (!path.startsWith('/')) return `${FACTORY_AGENT_BASE_URL}/${path}`
  return `${FACTORY_AGENT_BASE_URL}${path}`
}

async function parseErrorBody(res) {
  try {
    const text = await res.text()
    if (!text) return `${res.status} ${res.statusText}`
    try {
      const json = JSON.parse(text)
      if (typeof json.detail === 'string') return json.detail
      if (json.detail && typeof json.detail === 'object') return JSON.stringify(json.detail)
      return json.message || json.error || text
    } catch {
      return text
    }
  } catch {
    return `${res.status} ${res.statusText}`
  }
}

async function request(method, path, body, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  const token = options.bearerToken || STATIC_BEARER
  if (token) headers.Authorization = `Bearer ${token}`

  const init = { method, headers }
  if (body !== undefined) init.body = JSON.stringify(body)

  const startedAt = Date.now()
  const url = buildUrl(path)
  logger.debug(`[factory-agent] -> ${method} ${path}`, body)

  let response
  try {
    response = await fetch(url, init)
  } catch (err) {
    const e = new Error(normalizeFactoryAgentError(err, `Cannot connect to factory-agent: ${err?.message || 'network error'}`))
    e.type = 'NETWORK'
    e.original = err
    throw e
  }

  logger.apiRequest(method, `factory-agent${path}`, Date.now() - startedAt, response.status)

  if (!response.ok) {
    const detail = await parseErrorBody(response)
    const e = new Error(normalizeFactoryAgentError({ status: response.status, message: detail }, `${response.status} ${response.statusText}`))
    e.status = response.status
    e.type = response.status === 401 ? 'AUTH' : response.status === 404 ? 'NOT_FOUND' : response.status === 409 ? 'CONFLICT' : response.status === 429 ? 'RATE_LIMIT' : response.status >= 500 ? 'SERVER' : 'CLIENT'
    e.path = path
    throw e
  }

  const text = await response.text()
  if (!text) return null
  return JSON.parse(text)
}

export const factoryAgentApi = {
  createSession: ({ user_id }, options) => request('POST', '/sessions', { user_id }, options),
  getSession: (sessionId, options) => request('GET', `/sessions/${sessionId}`, undefined, options),
  getMessages: (sessionId, options) => request('GET', `/sessions/${sessionId}/messages`, undefined, options),
  getSteps: (sessionId, options) => request('GET', `/sessions/${sessionId}/steps`, undefined, options),

  addMessage: (sessionId, { content, role = 'user' }, options) =>
    request('POST', `/sessions/${sessionId}/messages`, { content, role }, options),

  createPlan: (sessionId, draft, options) => {
    const body = draft ? { draft } : {}
    return request('POST', `/sessions/${sessionId}/plans`, body, options)
  },

  execute: (sessionId, params = {}, options) => {
    const q = new URLSearchParams()
    if (params.background != null) q.set('background', String(Boolean(params.background)))
    if (params.expected_version != null) q.set('expected_version', String(params.expected_version))
    const suffix = q.toString() ? `?${q.toString()}` : ''
    return request('POST', `/sessions/${sessionId}/execute${suffix}`, {}, options)
  },

  cancelSession: (sessionId, options) => request('POST', `/sessions/${sessionId}/cancel`, {}, options),

  listPendingApprovals: (options) => request('GET', '/approvals/pending', undefined, options),
  getApproval: (approvalId, options) => request('GET', `/approvals/${approvalId}`, undefined, options),

  approve: (approvalId, payload = {}, options) =>
    request('POST', `/approvals/${approvalId}/approve`, payload, options),

  reject: (approvalId, payload = {}, options) =>
    request('POST', `/approvals/${approvalId}/reject`, payload, options),
}

export const FACTORY_AGENT_STATUS = {
  IDLE: 'IDLE',
  PLANNING: 'PLANNING',
  WAITING_APPROVAL: 'WAITING_APPROVAL',
  EXECUTING: 'EXECUTING',
  BLOCKED: 'BLOCKED',
  FAILED: 'FAILED',
  COMPLETED: 'COMPLETED',
}
