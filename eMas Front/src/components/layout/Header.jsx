import { Link } from 'react-router-dom'
import MobileMenu from './MobileMenu'
import logoBlack from '../../assets/logo-black.png'
import logoWhite from '../../assets/logo-white.png'
import { useThemeContext } from '../../context/ThemeContext'

const Header = () => {
  const { theme } = useThemeContext()

  return (
    <header className="bg-canvas border-b border-hairline h-[56px] px-4 flex items-center shrink-0 z-10">
      <div className="flex items-center justify-between w-full max-w-7xl mx-auto">
        <div className="flex items-center space-x-4">
          <MobileMenu />
          <Link to="/" className="flex items-center group md:hidden">
            <img
              src={theme === 'dark' ? logoBlack : logoWhite}
              alt="eMAS Logo"
              className="h-8 w-auto object-contain transition-transform group-hover:scale-105"
            />
          </Link>
        </div>
        <div className="flex items-center space-x-4 text-ink-muted">
          {/* User profile, notifications, theme toggle, etc. */}
        </div>
      </div>
    </header>
  )
}

export default Header
