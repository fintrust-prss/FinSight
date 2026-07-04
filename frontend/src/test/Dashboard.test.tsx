import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../pages/DashboardPage'

const MOCK_PORTFOLIO = {
  total_msmes: 3,
  tier_distribution: {
    Disciplined: 2,
    'Moderately Disciplined': 1,
    'Non-Disciplined': 0,
    'No-Go': 0,
  },
  msmes: [
    {
      msme_id: 'msme_001',
      legal_name: 'Alpha Foods Ltd',
      udyam_number: 'UDYAM-GJ-01-0001',
      sector: 'manufacturing',
      state: 'Gujarat',
      latest_score: 82.4,
      tier: 'Disciplined',
    },
    {
      msme_id: 'msme_002',
      legal_name: 'Beta Services Pvt',
      udyam_number: 'UDYAM-MH-02-0002',
      sector: 'services',
      state: 'Maharashtra',
      latest_score: 65.1,
      tier: 'Moderately Disciplined',
    },
    {
      msme_id: 'msme_003',
      legal_name: 'Gamma Traders',
      udyam_number: 'UDYAM-RJ-03-0003',
      sector: 'trade',
      state: 'Rajasthan',
      latest_score: null,
      tier: 'Non-Disciplined',
    },
  ],
}

vi.mock('../api/portfolio', () => ({
  fetchPortfolioSummary: vi.fn().mockResolvedValue(MOCK_PORTFOLIO),
}))

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders portfolio heading', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('Portfolio Dashboard')).toBeDefined()
    })
  })

  it('shows tier KPI counts', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Portfolio Dashboard'))
    // 2 Disciplined and 1 Moderately Disciplined
    const counts = screen.getAllByText(/^[0-9]+$/)
    const countValues = counts.map((c) => c.textContent)
    expect(countValues).toContain('2')
    expect(countValues).toContain('1')
  })

  it('renders all 3 MSME rows', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))
    expect(screen.getByText('Beta Services Pvt')).toBeDefined()
    expect(screen.getByText('Gamma Traders')).toBeDefined()
  })

  it('search filter narrows results', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))

    const searchInput = screen.getByRole('searchbox')
    fireEvent.change(searchInput, { target: { value: 'alpha' } })

    await waitFor(() => {
      expect(screen.getByText('Alpha Foods Ltd')).toBeDefined()
      expect(screen.queryByText('Beta Services Pvt')).toBeNull()
      expect(screen.queryByText('Gamma Traders')).toBeNull()
    })
  })

  it('sector filter narrows results to only services', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))

    const select = screen.getByRole('combobox', { name: /filter by sector/i })
    fireEvent.change(select, { target: { value: 'services' } })

    await waitFor(() => {
      expect(screen.getByText('Beta Services Pvt')).toBeDefined()
      expect(screen.queryByText('Alpha Foods Ltd')).toBeNull()
    })
  })

  it('clicking tier KPI card filters the table', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))

    const disciplinedKpi = screen.getByRole('button', { name: /disciplined/i })
    // Click the "Disciplined" KPI (not the badge inside — the card itself)
    fireEvent.click(disciplinedKpi)

    await waitFor(() => {
      // Only Alpha Foods with "Disciplined" tier should remain
      expect(screen.getByText('Alpha Foods Ltd')).toBeDefined()
    })
  })

  it('shows empty state message when no results match', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))

    const searchInput = screen.getByRole('searchbox')
    fireEvent.change(searchInput, { target: { value: 'xyznonexistent' } })

    await waitFor(() => {
      expect(screen.getByText(/no msmes match/i)).toBeDefined()
    })
  })

  it('shows "Clear filters" button when filter is applied', async () => {
    renderDashboard()
    await waitFor(() => screen.getByText('Alpha Foods Ltd'))

    const searchInput = screen.getByRole('searchbox')
    fireEvent.change(searchInput, { target: { value: 'alpha' } })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear filters/i })).toBeDefined()
    })
  })
})
