import { Link, useLocation } from 'react-router-dom'
import logoBlack from '../../assets/logo-black.png'
import logoWhite from '../../assets/logo-white.png'
import { useThemeContext } from '../../context/ThemeContext'
import { isNavItemActive, navSections, utilityNavItems } from './navigation'

const Sidebar = () => {
  const location = useLocation()
  const { theme } = useThemeContext()

  const isActive = (path) => isNavItemActive(location.pathname, path)

  return (
    <aside className="hidden md:flex sticky top-0 h-screen w-[280px] bg-canvas border-r border-hairline shrink-0 flex-col">
      <div className="flex h-full w-full flex-col">
        <div className="px-4 pb-4 pt-5 border-b border-hairline">
          <Link to="/" className="group flex h-12 items-center rounded-md px-2 outline-none transition-colors hover:bg-surface-1 focus-visible:ring-2 focus-visible:ring-primary-focus">
            <img
              src={theme === 'dark' ? logoBlack : logoWhite}
              alt="eMAS Logo"
              className="h-10 w-auto object-contain transition-transform group-hover:scale-[1.02]"
            />
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
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
                        aria-current={active ? 'page' : undefined}
                        className={`app-nav-link ${
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

        <div className="border-t border-hairline px-3 py-4">
          {utilityNavItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              aria-current={isActive(item.path) ? 'page' : undefined}
              className={`app-nav-link ${
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
    </aside>
  )
}

export default Sidebar
