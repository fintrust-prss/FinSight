import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMSMEProfile, fetchDataSources, postRescore } from '../api/msme'
import LoadingSpinner from '../components/LoadingSpinner'
import { ErrorCard } from '../components/ErrorBoundary'

const ALL_SOURCES = [
  {
    key: 'gst',
    label: 'GST Returns',
    icon: '📊',
    description: 'GSTR-1, GSTR-3B, GSTR-9 filings via NIC/GSTN',
  },
  {
    key: 'upi',
    label: 'UPI Transactions',
    icon: '💳',
    description: 'P2M/P2P transaction volume and velocity from NPCI',
  },
  {
    key: 'bank_statement',
    label: 'Bank Statements',
    icon: '🏦',
    description: 'Account balance, inflows, bounces via Account Aggregator',
  },
  {
    key: 'epfo',
    label: 'EPFO Records',
    icon: '👥',
    description: 'Employee count, wage bill and PF contributions',
  },
  {
    key: 'utility',
    label: 'Utility Bills',
    icon: '⚡',
    description: 'Electricity, water and gas consumption from Discom/BESCOM',
  },
  {
    key: 'digital_footprint',
    label: 'Digital Footprint',
    icon: '🌐',
    description: 'ONDC, e-commerce orders and Google Business Profile rating',
  },
]

export default function DataSourcePage() {
  const { id: msmeId } = useParams<{ id: string }>()
  const qc = useQueryClient()

  const profileQ = useQuery({
    queryKey: ['msme-profile', msmeId],
    queryFn: () => fetchMSMEProfile(msmeId!),
    enabled: !!msmeId,
  })

  const sourcesQ = useQuery({
    queryKey: ['msme-data-sources', msmeId],
    queryFn: () => fetchDataSources(msmeId!),
    enabled: !!msmeId,
  })

  const rescoreMut = useMutation({
    mutationFn: () => postRescore(msmeId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['msme-score', msmeId] })
      qc.invalidateQueries({ queryKey: ['msme-explain', msmeId] })
      qc.invalidateQueries({ queryKey: ['msme-history', msmeId] })
    },
  })

  if (profileQ.isLoading || sourcesQ.isLoading)
    return <LoadingSpinner variant="full" label="Loading data sources…" />

  if (profileQ.isError || sourcesQ.isError)
    return (
      <div className="page-error">
        <ErrorCard
          title="Failed to load data sources"
          onRetry={() => {
            profileQ.refetch()
            sourcesQ.refetch()
          }}
        />
      </div>
    )

  const profile = profileQ.data!
  const connected = new Set(sourcesQ.data!.connected_sources)

  return (
    <div className="data-source-page">
      {/* ── Breadcrumb ── */}
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/dashboard" className="breadcrumb__link">Dashboard</Link>
        <span className="breadcrumb__sep" aria-hidden="true">/</span>
        <Link to={`/msme/${msmeId}`} className="breadcrumb__link">{profile.legal_name}</Link>
        <span className="breadcrumb__sep" aria-hidden="true">/</span>
        <span className="breadcrumb__current">Data Sources</span>
      </nav>

      {/* ── Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Source Explorer</h1>
          <p className="page-subtitle">
            {connected.size} of {ALL_SOURCES.length} sources connected ·{' '}
            {sourcesQ.data!.consent_count} consent record
            {sourcesQ.data!.consent_count !== 1 ? 's' : ''}
          </p>
        </div>

        <button
          id="btn-rescore"
          className="btn btn--primary"
          disabled={rescoreMut.isPending || rescoreMut.isSuccess}
          onClick={() => rescoreMut.mutate()}
        >
          {rescoreMut.isPending ? (
            <>
              <span className="btn-spinner" aria-hidden="true" /> Rescoring…
            </>
          ) : rescoreMut.isSuccess ? (
            '✓ Rescore Queued'
          ) : (
            '⟳ Trigger Rescore'
          )}
        </button>
      </div>

      {rescoreMut.isSuccess && (
        <div className="info-banner" role="status">
          ✓ Background rescore queued successfully. Score will update in a moment.
        </div>
      )}

      {/* ── Source Cards ── */}
      <div className="source-grid">
        {ALL_SOURCES.map((src) => {
          const isConnected = connected.has(src.key)
          return (
            <div
              key={src.key}
              id={`source-card-${src.key}`}
              className={`source-card${isConnected ? ' source-card--connected' : ''}`}
              aria-label={`${src.label}: ${isConnected ? 'Connected' : 'Not connected'}`}
            >
              <div className="source-card__header">
                <span className="source-card__icon" aria-hidden="true">{src.icon}</span>
                <span
                  className={`source-card__status${isConnected ? ' source-card__status--on' : ''}`}
                >
                  {isConnected ? '● Connected' : '○ Not Connected'}
                </span>
              </div>
              <h3 className="source-card__title">{src.label}</h3>
              <p className="source-card__desc">{src.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
