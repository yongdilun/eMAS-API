import { useCallback, useEffect, useRef } from 'react'

const FACTORY_AGENT_BASE_URL = (
  import.meta.env?.VITE_FACTORY_AGENT_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

/**
 * useSessionEvents
 *
 * Opens GET /sessions/{sessionId}/events (Option C notification stream).
 * On every `snapshot_invalidated` or `phase_changed` frame, calls onInvalidate()
 * so the caller can re-fetch /snapshot. All UI state stays snapshot-derived.
 *
 * Falls back to a plain interval poll (fallbackMs, default 5 000) when:
 *   - sessionId is null / undefined
 *   - EventSource is unavailable
 *   - the SSE connection errors out
 *
 * The hook self-manages reconnection with exponential back-off (max 30 s).
 *
 * @param {string|null} sessionId
 * @param {() => void} onInvalidate   called whenever a new snapshot is needed
 * @param {{ enabled?: boolean, fallbackMs?: number }} [options]
 */
export function useSessionEvents(sessionId, onInvalidate, options = {}) {
  const { enabled = true, fallbackMs = 5000 } = options

  const onInvalidateRef = useRef(onInvalidate)
  onInvalidateRef.current = onInvalidate

  const esRef = useRef(null)
  const fallbackTimerRef = useRef(null)
  const retryTimerRef = useRef(null)
  const retryDelayRef = useRef(500)
  const lastCursorRef = useRef(null)
  const mountedRef = useRef(true)

  const stopFallback = useCallback(() => {
    if (fallbackTimerRef.current) {
      clearInterval(fallbackTimerRef.current)
      fallbackTimerRef.current = null
    }
  }, [])

  const startFallback = useCallback(() => {
    stopFallback()
    if (!fallbackMs || !sessionId) return
    fallbackTimerRef.current = setInterval(() => {
      onInvalidateRef.current?.()
    }, fallbackMs)
  }, [fallbackMs, sessionId, stopFallback])

  const closeEs = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    if (!sessionId || !enabled) return
    if (typeof EventSource === 'undefined') {
      startFallback()
      return
    }

    closeEs()

    const url = `${FACTORY_AGENT_BASE_URL}/sessions/${sessionId}/events`
    const es = new EventSource(url, { withCredentials: false })

    esRef.current = es

    es.addEventListener('notification', (evt) => {
      if (!mountedRef.current) return
      try {
        const frame = JSON.parse(evt.data)
        const frameType = frame?.type

        if (frameType === 'hello') {
          const cursor = typeof frame.cursor === 'number' ? frame.cursor : null
          if (cursor !== null && cursor !== lastCursorRef.current) {
            lastCursorRef.current = cursor
            onInvalidateRef.current?.()
          }
          stopFallback()
          retryDelayRef.current = 500
        }

        if (frameType === 'snapshot_invalidated' || frameType === 'phase_changed') {
          const cursor = typeof frame.cursor === 'number' ? frame.cursor : null
          if (cursor !== null && cursor !== lastCursorRef.current) {
            lastCursorRef.current = cursor
            onInvalidateRef.current?.()
          }
        }
      } catch {
        // malformed frame — ignore
      }
    })

    es.onerror = () => {
      if (!mountedRef.current) return
      closeEs()
      startFallback()
      const delay = retryDelayRef.current
      retryDelayRef.current = Math.min(delay * 2, 30000)
      retryTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect()
      }, delay)
    }
  }, [sessionId, enabled, closeEs, startFallback, stopFallback])

  useEffect(() => {
    mountedRef.current = true
    if (!sessionId || !enabled) {
      closeEs()
      stopFallback()
      return
    }
    retryDelayRef.current = 500
    connect()
    return () => {
      mountedRef.current = false
      closeEs()
      stopFallback()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, enabled])

  // When sessionId changes, reset cursor tracking.
  useEffect(() => {
    lastCursorRef.current = null
  }, [sessionId])
}
