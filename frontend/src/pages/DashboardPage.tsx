import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchPortfolioSummary } from '../api/portfolio'
import type { MSMESummary, Tier } from '../api/portfolio'
import TierBadge, { tierHex } from '../components/TierBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { ErrorCard } from '../components/ErrorBoundary'

const TIER_ORDER: Tier[] = [
  'Disciplined',
  'Moderately Disciplined',
  'Non-Disciplined',
  'No-Go',
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filterTier, setFilterTier] = useState<Tier | ''>('')
  const [filterSector, setFilterSector] = useState('')

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['portfolio-summary'],
    queryFn: fetchPortfolioSummary,
    staleTime: 60_000,
  })

  const sectors = useMemo(() => {
    if (!data) return []
    return [...new Set(data.msmes.map((m) => m.sector))].sort()
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return data.msmes.filter((m) => {
      const matchSearch =
        !search ||
        m.legal_name.toLowerCase().includes(search.toLowerCase()) ||
        m.udyam_number.toLowerCase().includes(search.toLowerCase())
      const matchTier = !filterTier || m.tier === filterTier
      const matchSector = !filterSector || m.sector === filterSector
      return matchSearch && matchTier && matchSector
    })
  }, [data, search, filterTier, filterSector])

  if (isLoading) return <LoadingSpinner variant="full" label="Loading portfolio…" />
  if (isError)
    return (
      <div className="page-error">
        <ErrorCard
          title="Failed to load portfolio"
          message={(error as any)?.message}
          onRetry={() => refetch()}
        />
      </div>
    )

  const dist = data!.tier_distribution

  return (
    <div className="dashboard-page">
      {/* ── Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Portfolio Dashboard</h1>
          <p className="page-subtitle">
            {data!.total_msmes} MSMEs onboarded · Risk summary
          </p>
        </div>
      </div>

      {/* ── KPI Strip ── */}
      <div className="kpi-strip" aria-label="Portfolio tier summary">
        {TIER_ORDER.map((tier) => (
          <button
            key={tier}
            id={`kpi-${tier.replace(/\s+/g, '-').toLowerCase()}`}
            className={`kpi-card${filterTier === tier ? ' kpi-card--active' : ''}`}
            style={{ '--tier-color': tierHex(tier) } as React.CSSProperties}
            onClick={() => setFilterTier(filterTier === tier ? '' : tier)}
            aria-pressed={filterTier === tier}
          >
            <span className="kpi-card__count">{dist[tier]}</span>
            <TierBadge tier={tier} />
          </button>
        ))}
      </div>

      {/* ── Filters ── */}
      <div className="filters-row">
        <input
          id="search-msme"
          type="search"
          className="form-input filters-row__search"
          placeholder="Search by name or Udyam number…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search MSMEs"
        />

        <select
          id="filter-sector"
          className="form-input form-select filters-row__select"
          value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)}
          aria-label="Filter by sector"
        >
          <option value="">All Sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>

        {(search || filterTier || filterSector) && (
          <button
            id="btn-clear-filters"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              setSearch('')
              setFilterTier('')
              setFilterSector('')
            }}
          >
            Clear filters
          </button>
        )}

        <span className="filters-row__count">
          {filtered.length} of {data!.total_msmes}
        </span>
      </div>

      {/* ── MSME Table ── */}
      <div className="table-wrap">
        <table className="msme-table" id="msme-table">
          <thead>
            <tr>
              <th scope="col">Business Name</th>
              <th scope="col">Udyam No.</th>
              <th scope="col">Sector</th>
              <th scope="col">State</th>
              <th scope="col">Score</th>
              <th scope="col">Tier</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty">
                  No MSMEs match your filters.
                </td>
              </tr>
            ) : (
              filtered.map((m) => (
                <MSMERow key={m.msme_id} msme={m} onClick={() => navigate(`/msme/${m.msme_id}`)} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MSMERow({
  msme,
  onClick,
}: {
  msme: MSMESummary
  onClick: () => void
}) {
  const score = msme.latest_score

  return (
    <tr
      className="msme-row"
      onClick={onClick}
      tabIndex={0}
      role="button"
      aria-label={`View health card for ${msme.legal_name}`}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
    >
      <td className="msme-row__name">{msme.legal_name}</td>
      <td className="msme-row__udyam">
        <code>{msme.udyam_number}</code>
      </td>
      <td className="msme-row__sector">
        {msme.sector.charAt(0).toUpperCase() + msme.sector.slice(1)}
      </td>
      <td>{msme.state}</td>
      <td className="msme-row__score">
        {score !== null ? (
          <span
            className="score-pill"
            style={{
              '--score-color': tierHex(msme.tier),
            } as React.CSSProperties}
          >
            {score.toFixed(1)}
          </span>
        ) : (
          <span className="score-pill score-pill--unscored">—</span>
        )}
      </td>
      <td>
        <TierBadge tier={msme.tier} />
      </td>
    </tr>
  )
}
