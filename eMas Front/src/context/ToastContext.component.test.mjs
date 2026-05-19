import assert from 'node:assert/strict'
import test from 'node:test'
import {
  React,
  createViteSsrServer,
  installDom,
  render,
  waitFor,
} from '../test/reactComponentTestUtils.mjs'

let server
let cleanupDom

test.before(async () => {
  cleanupDom = installDom()
  server = await createViteSsrServer()
})

test.after(async () => {
  await server?.close()
  cleanupDom?.()
})

function countToastMessages(container, message) {
  return Array.from(container.querySelectorAll('p')).filter(
    (node) => node.textContent.trim() === message,
  ).length
}

async function renderToastRun(run) {
  const { ToastProvider, useToast } = await server.ssrLoadModule('/src/context/ToastContext.jsx')

  const ToastRunner = () => {
    const toast = useToast()
    const hasRun = React.useRef(false)

    React.useEffect(() => {
      if (hasRun.current) return
      hasRun.current = true
      run(toast)
    }, [run, toast])

    return null
  }

  return render(
    React.createElement(
      ToastProvider,
      null,
      React.createElement(ToastRunner),
    ),
  )
}

test('ToastProvider dedupes repeated session-expired errors with the same dedupe key', async () => {
  const message = 'Your session has expired. Please refresh and try again.'
  const view = await renderToastRun((toast) => {
    toast.error(message, { dedupeKey: 'auth-expired', duration: 0 })
    toast.error(message, { dedupeKey: 'auth-expired', duration: 0 })
    toast.error(message, { dedupeKey: 'auth-expired', duration: 0 })
  })

  await waitFor(() => assert.equal(countToastMessages(view.container, message), 1))

  await view.unmount()
})

test('ToastProvider allows different messages or different dedupe keys', async () => {
  const sessionExpired = 'Your session has expired. Please refresh and try again.'
  const retryLater = 'Could not save settings. Try again later.'
  const view = await renderToastRun((toast) => {
    toast.error(sessionExpired, { dedupeKey: 'auth-expired', duration: 0 })
    toast.error(retryLater, { dedupeKey: 'auth-expired', duration: 0 })
    toast.error(sessionExpired, { dedupeKey: 'settings-save', duration: 0 })
  })

  await waitFor(() => {
    assert.equal(view.container.querySelectorAll('p').length, 3)
    assert.equal(countToastMessages(view.container, sessionExpired), 2)
    assert.equal(countToastMessages(view.container, retryLater), 1)
  })

  await view.unmount()
})
