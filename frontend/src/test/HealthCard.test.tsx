import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import HealthCardPage from '../pages/HealthCardPage'

// ── Mock API modules ──────────────────────────────────────────────────────────
vi.mock('../api/msme', () => ({
  fetchMSMEProfile: vi.fn().mockResolvedValue({
    id: 1,
    msme_id: 'msme_test_001',
    legal_name: 'Test Foods Pvt Ltd',
    udyam_number: 'UDYAM-GJ-01-0012345',
    sector: 'manufacturing',
    sub_sector: 'food_processing',
    vintage_years: 5,
    state: 'Gujarat',
    registration_type: 'private_limited',
    created_at: '2024-01-01T00:00:00Z',
  }),
  fetchMSMEScore: vi.fn().mockResolvedValue({
    msme_id: 'msme_test_001',
    overall_score: 78.5,
    tier: 'Disciplined',
    as_of_date: '2026-07-04',
    dimension_scores: {
      revenue_cashflow: 82,
      compliance_formalization: 75,
      repayment_creditworthiness: 70,
      operational_stability: 80,
      workforce_employment: 65,
      digital_ecosystem: 90,
      bureau_credit_history: 85,
    },
    model_version: 'v1.2.0',
  }),
  fetchMSMEExplain: vi.fn().mockResolvedValue({
    msme_id: 'msme_test_001',
    shap_summary: {
      revenue_cashflow: 0.12,
      compliance_formalization: 0.08,
      repayment_creditworthiness: -0.03,
      digital_ecosystem: 0.15,
    },
    reasons: {},
  }),
  fetchMSMEHistory: vi.fn().mockResolvedValue([]),
  postConsent: vi.fn().mockResolvedValue({
    consent_id: 'consent_test_001',
    msme_id: 'msme_test_001',
    data_types: ['gst', 'upi'],
    purpose: 'Credit Scoring Assessment',
    status: 'ACTIVE',
    expiry: '2026-07-05T00:00:00Z',
  }),
}))

function renderHealthCard(msmeId = 'msme_test_001') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/msme/${msmeId}`]}>
        <Routes>
          <Route path="/msme/:id" element={<HealthCardPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HealthCardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the MSME legal name after loading', async () => {
    renderHealthCard()
    await waitFor(() => {
      expect(screen.getByText('Test Foods Pvt Ltd')).toBeDefined()
    })
  })

  it('renders overall score and Disciplined tier badge', async () => {
    renderHealthCard()
    await waitFor(() => {
      expect(screen.getByText('78.5')).toBeDefined()
    })
    expect(screen.getByText('Disciplined')).toBeDefined()
  })

  it('renders the radar chart tab and switches views', async () => {
    renderHealthCard()
    await waitFor(() => screen.getByText('Test Foods Pvt Ltd'))

    // Default tab is radar
    const radarTab = screen.getByRole('tab', { name: /radar/i })
    expect(radarTab.getAttribute('aria-selected')).toBe('true')

    // Click gauge tab
    const gaugeTab = screen.getByRole('tab', { name: /gauge/i })
    fireEvent.click(gaugeTab)
    expect(gaugeTab.getAttribute('aria-selected')).toBe('true')

    // Click SHAP tab
    const shapTab = screen.getByRole('tab', { name: /why this score/i })
    fireEvent.click(shapTab)
    expect(shapTab.getAttribute('aria-selected')).toBe('true')
  })

  it('shows all 7 dimension cards in radar view', async () => {
    renderHealthCard()
    await waitFor(() => screen.getByText('Test Foods Pvt Ltd'))
    // Score numbers should appear in the dimension grid
    expect(screen.getAllByRole('progressbar').length).toBe(7)
  })

  it('shows consent gate when score returns 403', async () => {
    const { fetchMSMEScore } = await import('../api/msme')
    const mockErr = { response: { status: 403 } }
    vi.mocked(fetchMSMEScore).mockRejectedValueOnce(mockErr)

    renderHealthCard()
    await waitFor(() => screen.getByText('Test Foods Pvt Ltd'))
    await waitFor(() => {
      expect(
        screen.getByText(/Account Aggregator Consent Required/i),
      ).toBeDefined()
    })
  })

  it('renders "Grant AA Consent" button in consent gate panel', async () => {
    const { fetchMSMEScore } = await import('../api/msme')
    const mockErr = { response: { status: 403 } }
    vi.mocked(fetchMSMEScore).mockRejectedValueOnce(mockErr)

    renderHealthCard()
    await waitFor(() => screen.getByText('Test Foods Pvt Ltd'))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /grant aa consent/i })).toBeDefined()
    })
  })

  it('shows data sources link', async () => {
    renderHealthCard()
    await waitFor(() => screen.getByText('Test Foods Pvt Ltd'))
    expect(screen.getByText('Data Sources')).toBeDefined()
  })
})
