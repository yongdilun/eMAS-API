import { Link, useLocation } from 'react-router-dom'
import logoBlack from '../../assets/logo-black.png'
import logoWhite from '../../assets/logo-white.png'
import { useThemeContext } from '../../context/ThemeContext'
import { isNavItemActive, navSections, utilityNavItems } from './navigation'

const Sidebar = ({ collapsed, onCollapsedChange }) => {
  const location = useLocation()
  const { theme } = useThemeContext()

  const isActive = (path) => isNavItemActive(location.pathname, path)

  return (
    <aside
      className={`hidden md:flex sticky top-0 h-screen shrink-0 flex-col border-r border-hairline bg-canvas transition-[width] duration-300 ease-out ${
        collapsed ? 'w-[72px]' : 'w-[280px]'
      }`}
    >
      <div className="flex h-full w-full min-w-0 flex-col">
        <div className="flex items-center border-b border-hairline px-3 pb-4 pt-5">
          {collapsed ? (
            <div className="flex w-full justify-center">
              <button
                type="button"
                onClick={() => onCollapsedChange(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-1 text-ink-muted transition-colors hover:border-hairline-strong hover:bg-surface-2 hover:text-ink"
                aria-label="Expand sidebar"
                title="Expand sidebar"
              >
                <span className="material-symbols-outlined text-[22px]">chevron_right</span>
              </button>
            </div>
          ) : (
            <>
              <Link
                to="/"
                title="Home"
                className="group flex h-12 min-w-0 flex-1 shrink-0 items-center rounded-md px-2 outline-none transition-colors hover:bg-surface-1 focus-visible:ring-2 focus-visible:ring-primary-focus"
              >
                <img
                  src={theme === 'dark' ? logoBlack : logoWhite}
                  alt="eMAS Logo"
                  className="h-10 w-auto object-contain transition-transform group-hover:scale-[1.02]"
                />
              </Link>
              <button
                type="button"
                onClick={() => onCollapsedChange(true)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-1 text-ink-muted transition-colors hover:border-hairline-strong hover:bg-surface-2 hover:text-ink"
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
              >
                <span className="material-symbols-outlined text-[22px]">dock_to_right</span>
              </button>
            </>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
          <div className="flex flex-col gap-5">
            {navSections.map((section) => (
              <section key={section.label} className="app-nav-section" aria-label={section.label}>
                <p
                  className={`px-3 text-eyebrow uppercase text-ink-tertiary transition-opacity duration-200 ${
                    collapsed ? 'sr-only' : ''
                  }`}
                >
                  {section.label}
                </p>
                <div className={`mt-2 flex flex-col gap-1 ${collapsed ? 'mt-0' : ''}`}>
                  {section.items.map((item) => {
                    const active = isActive(item.path)
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        title={collapsed ? item.label : undefined}
                        aria-current={active ? 'page' : undefined}
                        className={`app-nav-link ${collapsed ? 'justify-center px-2' : ''} ${
                          active
                            ? 'app-nav-link-active'
                            : 'text-ink-muted hover:bg-surface-1 hover:text-ink'
                        }`}
                      >
                        <span className="app-nav-active-marker" aria-hidden="true" />
                        <span
                          className={`material-symbols-outlined app-nav-icon shrink-0 ${
                            active ? 'text-ink' : 'text-ink-muted'
                          }`}
                          style={
                            active
                              ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" }
                              : {}
                          }
                        >
                          {item.icon}
                        </span>
                        <span
                          className={`min-w-0 truncate text-button transition-opacity duration-200 ${
                            collapsed ? 'sr-only' : ''
                          }`}
                        >
                          {item.label}
                        </span>
                      </Link>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </nav>

        <div className="border-t border-hairline px-3 py-4">
          {utilityNavItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              title={collapsed ? item.label : undefined}
              aria-current={isActive(item.path) ? 'page' : undefined}
              className={`app-nav-link ${collapsed ? 'justify-center px-2' : ''} ${
                isActive(item.path)
                  ? 'app-nav-link-active'
                  : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
              }`}
            >
              <span className="app-nav-active-marker" aria-hidden="true" />
              <span
                className={`material-symbols-outlined app-nav-icon shrink-0 ${
                  isActive(item.path) ? 'text-ink' : 'text-ink-muted'
                }`}
                style={
                  isActive(item.path)
                    ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" }
                    : {}
                }
              >
                {item.icon}
              </span>
              <span
                className={`min-w-0 truncate text-button transition-opacity duration-200 ${
                  collapsed ? 'sr-only' : ''
                }`}
              >
                {item.label}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
