import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import logoBlack from '../../assets/logo-black.png'
import logoWhite from '../../assets/logo-white.png'
import { useThemeContext } from '../../context/ThemeContext'
import { isNavItemActive, navSections, utilityNavItems } from './navigation'

const MobileMenu = () => {
  const [isOpen, setIsOpen] = useState(false)
  const location = useLocation()
  const { theme } = useThemeContext()

  const isActive = (path) => isNavItemActive(location.pathname, path)

  return (
    <div className="md:hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-md hover:bg-surface-2 text-ink-muted hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-focus"
        aria-label="Open navigation"
        aria-expanded={isOpen}
      >
        <span className="material-symbols-outlined">
          {isOpen ? 'close' : 'menu'}
        </span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 bg-canvas overflow-y-auto">
          <div className="flex min-h-full flex-col">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-4">
              <Link to="/" onClick={() => setIsOpen(false)} className="flex h-11 items-center rounded-md px-2 hover:bg-surface-1">
                <img
                  src={theme === 'dark' ? logoBlack : logoWhite}
                  alt="eMAS Logo"
                  className="h-9 w-auto object-contain"
                />
              </Link>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-md hover:bg-surface-2 text-ink-muted hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-focus"
                aria-label="Close navigation"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <nav className="flex-1 px-4 py-5">
              <div className="flex flex-col gap-5">
                {navSections.map((section) => (
                  <section key={section.label} className="app-nav-section">
                    <p className="px-3 text-eyebrow uppercase text-ink-tertiary">{section.label}</p>
                    <div className="mt-2 flex flex-col gap-1">
                      {section.items.map((item) => {
                        const active = isActive(item.path)
                        return (
                          <Link
                            key={item.path}
                            to={item.path}
                            onClick={() => setIsOpen(false)}
                            aria-current={active ? 'page' : undefined}
                            className={`app-nav-link min-h-11 ${
                              active
                                ? 'app-nav-link-active'
                                : 'text-ink-muted hover:bg-surface-1 hover:text-ink'
                            }`}
                          >
                            <span className="app-nav-active-marker" aria-hidden="true" />
                            <span
                              className={`material-symbols-outlined app-nav-icon ${
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
                            <span className="min-w-0 truncate text-button">{item.label}</span>
                          </Link>
                        )
                      })}
                    </div>
                  </section>
                ))}
              </div>
            </nav>

            <div className="border-t border-hairline px-4 py-4">
              {utilityNavItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  aria-current={isActive(item.path) ? 'page' : undefined}
                  className={`app-nav-link min-h-11 ${
                    isActive(item.path)
                      ? 'app-nav-link-active'
                      : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
                  }`}
                >
                  <span className="app-nav-active-marker" aria-hidden="true" />
                  <span
                    className={`material-symbols-outlined app-nav-icon ${
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
                  <span className="min-w-0 truncate text-button">{item.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MobileMenu
