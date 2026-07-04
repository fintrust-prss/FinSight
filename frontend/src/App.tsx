import { Routes, Route, Navigate } from 'react-router-dom'

/**
 * Root application component.
 *
 * Defines the 5 screens from spec Section 10:
 *   1. /login          — Bank officer login (demo auth)
 *   2. /dashboard      — Portfolio overview (all MSMEs)
 *   3. /msme/:id       — MSME Financial Health Card (centerpiece)
 *   4. /msme/:id/data  — Data Source Explorer
 *   5. /ecosystem      — ULI/OCEN/AA connector status
 *
 * Page components will be implemented in Phase 6.
 * This file defines the routing shell — ready to receive components.
 */
function App() {
  return (
    <Routes>
      {/* Redirect root to dashboard (or login if unauthenticated — Phase 5 guards) */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Phase 6: Replace placeholders with real page components */}
      <Route path="/login" element={<PlaceholderPage title="Login" />} />
      <Route path="/dashboard" element={<PlaceholderPage title="Portfolio Dashboard" />} />
      <Route path="/msme/:id" element={<PlaceholderPage title="MSME Health Card" />} />
      <Route path="/msme/:id/data" element={<PlaceholderPage title="Data Source Explorer" />} />
      <Route path="/ecosystem" element={<PlaceholderPage title="Ecosystem Status" />} />

      {/* 404 fallback */}
      <Route path="*" element={<PlaceholderPage title="404 — Page Not Found" />} />
    </Routes>
  )
}

/** Temporary placeholder rendered until Phase 6 page components are built. */
function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="placeholder-page">
      <div className="placeholder-card">
        <div className="placeholder-badge">Phase 0 Scaffold</div>
        <h1>{title}</h1>
        <p>
          This page will be implemented in{' '}
          <strong>Phase 6 — Frontend Application</strong>.
        </p>
        <p>
          Backend API is running at{' '}
          <a href={import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'} target="_blank" rel="noreferrer">
            {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
          </a>
        </p>
        <a href="/dashboard" className="placeholder-link">→ Portfolio Dashboard</a>
      </div>
    </div>
  )
}

export default App
