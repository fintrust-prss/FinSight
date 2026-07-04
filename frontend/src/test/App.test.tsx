import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

// Mock all API modules so routing tests don't make real HTTP calls
vi.mock('../api/auth', () => ({
  postLogin: vi.fn(),
}))
vi.mock('../api/portfolio', () => ({
  fetchPortfolioSummary: vi.fn().mockResolvedValue({
    total_msmes: 0,
    tier_distribution: {
      Disciplined: 0,
      'Moderately Disciplined': 0,
      'Non-Disciplined': 0,
      'No-Go': 0,
    },
    msmes: [],
  }),
}))
vi.mock('../api/msme', () => ({
  fetchMSMEProfile: vi.fn().mockResolvedValue({
    id: 1, msme_id: 'msme_001', legal_name: 'Test MSME', udyam_number: 'U-001',
    sector: 'manufacturing', sub_sector: 'food', vintage_years: 3, state: 'Gujarat',
    registration_type: 'private_limited', created_at: null,
  }),
  fetchMSMEScore: vi.fn().mockRejectedValue({ response: { status: 403 } }),
  fetchMSMEExplain: vi.fn().mockRejectedValue(new Error('403')),
  fetchMSMEHistory: vi.fn().mockResolvedValue([]),
  fetchDataSources: vi.fn().mockResolvedValue({ msme_id: 'msme_001', connected_sources: [], consent_count: 0 }),
  postConsent: vi.fn(),
  postRescore: vi.fn(),
}))
vi.mock('../api/ecosystem', () => ({
  fetchULIStatus: vi.fn().mockResolvedValue({
    connector_id: 'uli_01', status: 'ONLINE', ping_latency_ms: 14, connected_since: '2026-07-01T00:00:00Z', last_heartbeat: '2026-07-04T12:00:00Z',
  }),
  fetchOCENStatus: vi.fn().mockResolvedValue({
    connector_id: 'ocen_01', status: 'ONLINE', ping_latency_ms: 22, connected_since: '2026-07-01T00:00:00Z', last_heartbeat: '2026-07-04T12:00:00Z',
  }),
}))

function renderApp(initialPath = '/', authenticated = false) {
  // Seed localStorage for authenticated tests
  if (authenticated) {
    localStorage.setItem('fs_token', 'fake_test_token')
    localStorage.setItem('fs_role', 'bank_officer')
    localStorage.setItem('fs_username', 'test_officer')
  } else {
    localStorage.clear()
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App routing — Phase 6', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('redirects unauthenticated / to /login', async () => {
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByText('Sign in to FinSight')).toBeDefined()
    })
  })

  it('renders login page at /login when unauthenticated', async () => {
    renderApp('/login')
    expect(screen.getByText('FinSight')).toBeDefined()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined()
  })

  it('shows dashboard when authenticated and navigating to /dashboard', async () => {
    renderApp('/dashboard', true)
    await waitFor(() => {
      expect(screen.getByText('Portfolio Dashboard')).toBeDefined()
    })
  })

  it('redirects /dashboard to /login when not authenticated', () => {
    renderApp('/dashboard', false)
    expect(screen.getByText('Sign in to FinSight')).toBeDefined()
  })

  it('shows ecosystem page at /ecosystem when authenticated', async () => {
    renderApp('/ecosystem', true)
    await waitFor(() => {
      expect(screen.getByText('Ecosystem Status')).toBeDefined()
    })
  })

  it('renders 404 for unknown routes', () => {
    renderApp('/this-route-does-not-exist')
    expect(screen.getByText(/404/i)).toBeDefined()
  })
})
