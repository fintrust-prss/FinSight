import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import HealthCardPage from './pages/HealthCardPage'
import DataSourcePage from './pages/DataSourcePage'
import EcosystemPage from './pages/EcosystemPage'

/**
 * Root application component — Phase 6 implementation.
 *
 * Screens from spec Section 10:
 *   1. /login          — Bank officer login (demo auth)
 *   2. /dashboard      — Portfolio overview (all MSMEs)
 *   3. /msme/:id       — MSME Financial Health Card
 *   4. /msme/:id/data  — Data Source Explorer
 *   5. /ecosystem      — ULI/OCEN connector status
 */
function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — wrapped in Layout shell */}
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/msme/:id" element={<HealthCardPage />} />
          <Route path="/msme/:id/data" element={<DataSourcePage />} />
          <Route path="/ecosystem" element={<EcosystemPage />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}

function NotFoundPage() {
  return (
    <div className="placeholder-page">
      <div className="placeholder-card">
        <div className="placeholder-badge">Error 404</div>
        <h1>Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/dashboard" className="placeholder-link">
          → Back to Dashboard
        </a>
      </div>
    </div>
  )
}

export default App
