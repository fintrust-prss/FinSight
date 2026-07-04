import { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const DEMO_USERS = [
  { label: 'Sharma (Bank Officer)', username: 'bank_officer_sharma', role: 'bank_officer' as const },
  { label: 'Priya (Underwriter)', username: 'underwriter_priya', role: 'underwriter' as const },
  { label: 'Admin', username: 'admin_user', role: 'admin' as const },
]

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as any)?.from?.pathname ?? '/dashboard'

  const [username, setUsername] = useState(DEMO_USERS[0].username)
  const [role, setRole] = useState<'bank_officer' | 'underwriter' | 'admin'>(
    DEMO_USERS[0].role,
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isAuthenticated) return <Navigate to={from} replace />

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await login(username, role)
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handlePresetClick(preset: (typeof DEMO_USERS)[0]) {
    setUsername(preset.username)
    setRole(preset.role)
  }

  return (
    <div className="login-page">
      <div className="login-glow login-glow--1" aria-hidden="true" />
      <div className="login-glow login-glow--2" aria-hidden="true" />

      <div className="login-card" role="main">
        {/* Logo */}
        <div className="login-brand">
          <div className="login-brand__icon" aria-hidden="true">⬡</div>
          <h1 className="login-brand__name">FinSight</h1>
          <p className="login-brand__tagline">MSME Credit Intelligence Platform</p>
        </div>

        {/* Demo presets */}
        <div className="login-presets">
          <p className="login-presets__label">Quick demo login</p>
          <div className="login-presets__list">
            {DEMO_USERS.map((u) => (
              <button
                key={u.username}
                id={`preset-${u.role}`}
                type="button"
                className={`login-preset-btn${username === u.username ? ' login-preset-btn--active' : ''}`}
                onClick={() => handlePresetClick(u)}
              >
                {u.label}
              </button>
            ))}
          </div>
        </div>

        <form id="login-form" className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login-username" className="form-label">
              Username
            </label>
            <input
              id="login-username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-role" className="form-label">
              Role
            </label>
            <select
              id="login-role"
              className="form-input form-select"
              value={role}
              onChange={(e) =>
                setRole(e.target.value as 'bank_officer' | 'underwriter' | 'admin')
              }
            >
              <option value="bank_officer">Bank Officer</option>
              <option value="underwriter">Underwriter</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {error && (
            <div className="form-error" role="alert">
              ⚠ {error}
            </div>
          )}

          <button
            id="btn-login"
            type="submit"
            className="btn btn--primary btn--full"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="btn-spinner" aria-hidden="true" /> Signing in…
              </>
            ) : (
              'Sign in to FinSight'
            )}
          </button>
        </form>

        <p className="login-notice">
          Demo environment — no real credentials required.
        </p>
      </div>
    </div>
  )
}
