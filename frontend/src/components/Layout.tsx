import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: '▦' },
  { to: '/ecosystem', label: 'Ecosystem', icon: '⬡' },
]

export default function Layout() {
  const { username, role, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const roleLabel =
    role === 'bank_officer'
      ? 'Bank Officer'
      : role === 'underwriter'
        ? 'Underwriter'
        : role === 'admin'
          ? 'Admin'
          : role ?? 'User'

  return (
    <div className="layout">
      {/* ── Top Nav ── */}
      <header className="topnav" role="banner">
        <div className="topnav__brand">
          <span className="topnav__logo-icon" aria-hidden="true">⬡</span>
          <span className="topnav__logo-text">FinSight</span>
          <span className="topnav__logo-sub">MSME Credit Intelligence</span>
        </div>

        <nav className="topnav__links" aria-label="Primary navigation">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              id={`nav-${label.toLowerCase()}`}
              className={({ isActive }) =>
                `topnav__link${isActive ? ' topnav__link--active' : ''}`
              }
            >
              <span aria-hidden="true">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="topnav__user">
          <div className="topnav__user-info">
            <span className="topnav__username">{username ?? 'Officer'}</span>
            <span className="topnav__role">{roleLabel}</span>
          </div>
          <button
            id="btn-logout"
            className="btn btn--ghost btn--sm"
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="layout__content" id="main-content">
        <Outlet />
      </main>
    </div>
  )
}
