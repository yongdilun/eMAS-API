import { useEffect, useState } from 'react'
import Sidebar from './Sidebar'

const SIDEBAR_COLLAPSED_KEY = 'emas-sidebar-collapsed'

const Layout = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? 'true' : 'false')
    } catch {
      /* ignore */
    }
  }, [sidebarCollapsed])

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-canvas text-ink">
      <Sidebar collapsed={sidebarCollapsed} onCollapsedChange={setSidebarCollapsed} />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-canvas">
        <div className="flex-1 overflow-auto">
          <div
            className={`w-full ${sidebarCollapsed ? 'max-w-none' : 'mx-auto max-w-7xl'}`}
          >
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}

export default Layout


