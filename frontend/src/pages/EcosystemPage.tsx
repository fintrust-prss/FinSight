import { useState } from 'react'
import { useQueries, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchULIStatus,
  fetchOCENStatus,
  initiateAAConsent,
  fetchPendingConsents,
  approveAAConsent,
  revokeAAConsent,
  fetchULIData,
  fetchOCENSignal,
} from '../api/ecosystem'
import { fetchPortfolioSummary } from '../api/portfolio'
import type { ConnectorStatus } from '../api/ecosystem'
import LoadingSpinner from '../components/LoadingSpinner'
import { ErrorCard } from '../components/ErrorBoundary'

function statusColor(status: string) {
  switch (status) {
    case 'ONLINE':
      return '#10b981'
    case 'DEGRADED':
      return '#f59e0b'
    default:
      return '#ef4444'
  }
}

function ConnectorCard({
  name,
  subtitle,
  data,
  isLoading,
  isError,
  onRetry,
}: {
  name: string
  subtitle: string
  data: ConnectorStatus | undefined
  isLoading: boolean
  isError: boolean
  onRetry: () => void
}) {
  return (
    <div
      id={`connector-${name.toLowerCase().replace(/[^a-z]/g, '-')}`}
      className={`connector-card${data?.status === 'ONLINE' ? ' connector-card--online' : ''}`}
    >
      <div className="connector-card__header">
        <div>
          <h2 className="connector-card__name">{name}</h2>
          <p className="connector-card__subtitle">{subtitle}</p>
        </div>
        {data && (
          <span
            className="connector-card__status-badge"
            style={{ background: `${statusColor(data.status)}22`, color: statusColor(data.status) }}
            role="status"
            aria-label={`Status: ${data.status}`}
          >
            <span
              className="connector-card__dot"
              style={{ background: statusColor(data.status) }}
              aria-hidden="true"
            />
            {data.status}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner label={`Fetching ${name} status…`} />}
      {isError && (
        <ErrorCard title={`${name} unavailable`} onRetry={onRetry} />
      )}

      {data && (
        <dl className="connector-card__details">
          <div className="connector-detail">
            <dt>Connector ID</dt>
            <dd>
              <code>{data.connector_id}</code>
            </dd>
          </div>
          <div className="connector-detail">
            <dt>Latency</dt>
            <dd>
              <span className={`latency-pill${data.ping_latency_ms < 50 ? ' latency-pill--fast' : ''}`}>
                {data.ping_latency_ms} ms
              </span>
            </dd>
          </div>
          <div className="connector-detail">
            <dt>Connected since</dt>
            <dd>{new Date(data.connected_since).toLocaleDateString('en-IN')}</dd>
          </div>
          <div className="connector-detail">
            <dt>Last heartbeat</dt>
            <dd>
              {new Date(data.last_heartbeat).toLocaleString('en-IN', {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}
            </dd>
          </div>
        </dl>
      )}
    </div>
  )
}

export default function EcosystemPage() {
  const qc = useQueryClient()
  const [selectedMsmeAA, setSelectedMsmeAA] = useState('')
  const [selectedMsmeULI, setSelectedMsmeULI] = useState('')
  const [selectedMsmeOCEN, setSelectedMsmeOCEN] = useState('')

  const [uliPayload, setUliPayload] = useState<any>(null)
  const [uliError, setUliError] = useState<string | null>(null)
  const [uliLoading, setUliLoading] = useState(false)

  const [ocenPayload, setOcenPayload] = useState<any>(null)
  const [ocenError, setOcenError] = useState<string | null>(null)
  const [ocenLoading, setOcenLoading] = useState(false)

  // Status queries
  const results = useQueries({
    queries: [
      {
        queryKey: ['ecosystem-uli'],
        queryFn: fetchULIStatus,
        staleTime: 30_000,
      },
      {
        queryKey: ['ecosystem-ocen'],
        queryFn: fetchOCENStatus,
        staleTime: 30_000,
      },
    ],
  })

  const [uliQ, ocenQ] = results

  // Fetch portfolio for dropdown selections
  const portfolioQ = useQuery({
    queryKey: ['portfolio-summary'],
    queryFn: fetchPortfolioSummary,
  })

  // Fetch pending consents list
  const pendingConsentsQ = useQuery({
    queryKey: ['pending-consents'],
    queryFn: fetchPendingConsents,
  })

  // Consent Mutations
  const initiateMut = useMutation({
    mutationFn: (msmeId: string) => initiateAAConsent(msmeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-consents'] })
    },
  })

  const approveMut = useMutation({
    mutationFn: (consentId: string) => approveAAConsent(consentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-consents'] })
    },
  })

  const revokeMut = useMutation({
    mutationFn: (consentId: string) => revokeAAConsent(consentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-consents'] })
    },
  })

  // Handlers for Sandbox
  const handleInitiateAA = () => {
    if (!selectedMsmeAA) return
    initiateMut.mutate(selectedMsmeAA)
  }

  const handleFetchULI = async () => {
    if (!selectedMsmeULI) return
    setUliLoading(true)
    setUliPayload(null)
    setUliError(null)
    try {
      const payload = await fetchULIData(selectedMsmeULI)
      setUliPayload(payload)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setUliError('Access Denied: Active AA Consent is required to retrieve ULI standardized files.')
      } else {
        setUliError(err.response?.data?.error?.message || 'Failed to fetch ULI standardized data.')
      }
    } finally {
      setUliLoading(false)
    }
  }

  const handleFetchOCEN = async () => {
    if (!selectedMsmeOCEN) return
    setOcenLoading(true)
    setOcenPayload(null)
    setOcenError(null)
    try {
      const payload = await fetchOCENSignal(selectedMsmeOCEN)
      setOcenPayload(payload)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setOcenError('Access Denied: Active AA Consent is required to generate OCEN LSP signal stubs.')
      } else {
        setOcenError(err.response?.data?.error?.message || 'Failed to fetch OCEN LSP signal stub.')
      }
    } finally {
      setOcenLoading(false)
    }
  }

  const msmesList = portfolioQ.data?.msmes || []

  return (
    <div className="ecosystem-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Ecosystem Status</h1>
          <p className="page-subtitle">
            Unified Lending Interface (ULI) and Open Credit Enablement Network
            (OCEN) connector health
          </p>
        </div>

        <button
          id="btn-refresh-ecosystem"
          className="btn btn--ghost btn--sm"
          onClick={() => {
            uliQ.refetch()
            ocenQ.refetch()
            pendingConsentsQ.refetch()
          }}
        >
          ↺ Refresh Status
        </button>
      </div>

      {/* ── AA Info Banner ── */}
      <div className="aa-info-card">
        <span className="aa-info-card__icon" aria-hidden="true">🏛</span>
        <div>
          <h3 className="aa-info-card__title">Account Aggregator (AA) Framework</h3>
          <p className="aa-info-card__body">
            Consent-based alternate data flows operate over the Sahamati AA
            network. Consent records are created via the{' '}
            <code>/api/v1/consent</code> or <code>/api/v1/ecosystem/aa/request</code> endpoints and gate access to MSME
            alternate data for credit scoring.
          </p>
        </div>
      </div>

      <div className="connector-grid">
        <ConnectorCard
          name="ULI — Unified Lending Interface"
          subtitle="RBI-mandated lending data exchange rail"
          data={uliQ.data}
          isLoading={uliQ.isLoading}
          isError={uliQ.isError}
          onRetry={() => uliQ.refetch()}
        />
        <ConnectorCard
          name="OCEN — Open Credit Enablement Network"
          subtitle="iSpirt credit protocol for embedded lending"
          data={ocenQ.data}
          isLoading={ocenQ.isLoading}
          isError={ocenQ.isError}
          onRetry={() => ocenQ.refetch()}
        />
      </div>

      <div className="page-header" style={{ marginTop: '2rem', marginBottom: '0px' }}>
        <div>
          <h2 className="page-title" style={{ fontSize: '1.5rem' }}>Ecosystem Integration Simulators (Sandbox)</h2>
          <p className="page-subtitle">Test consent-flow handshake and data-fetch pipelines end-to-end</p>
        </div>
      </div>

      <div className="sandbox-grid">
        {/* Left Column: AA Consent Sandbox */}
        <div className="sandbox-card">
          <h3 className="sandbox-card__title">
            <span role="img" aria-label="AA">🔑</span> Account Aggregator (AA) Simulator
          </h3>
          <p className="page-subtitle" style={{ fontSize: '0.85rem' }}>
            Request dynamic consent from a mock client, then grant or revoke access manually.
          </p>

          <div className="sandbox-form">
            <select
              className="sandbox-select"
              value={selectedMsmeAA}
              onChange={(e) => setSelectedMsmeAA(e.target.value)}
            >
              <option value="">-- Select MSME --</option>
              {msmesList.map((m) => (
                <option key={m.msme_id} value={m.msme_id}>
                  {m.legal_name} ({m.msme_id})
                </option>
              ))}
            </select>
            <button
              className="btn btn--primary btn--sm"
              disabled={!selectedMsmeAA || initiateMut.isPending}
              onClick={handleInitiateAA}
            >
              {initiateMut.isPending ? 'Initiating…' : 'Request Consent'}
            </button>
          </div>

          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: '1rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
            Simulated Consent Requests (Active/Pending)
          </h4>
          
          {pendingConsentsQ.isLoading ? (
            <LoadingSpinner label="Loading consents…" />
          ) : pendingConsentsQ.data && pendingConsentsQ.data.length > 0 ? (
            <div className="sandbox-list">
              {pendingConsentsQ.data.map((c) => (
                <div key={c.consent_id} className="sandbox-item">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span style={{ fontWeight: 600 }}>{c.msme_id}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      ID: <code>{c.consent_id}</code>
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      Expires: {new Date(c.expiry).toLocaleString('en-IN', { timeStyle: 'short', dateStyle: 'short' })}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        background: c.status === 'ACTIVE' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                        color: c.status === 'ACTIVE' ? '#10b981' : '#f59e0b',
                      }}
                    >
                      {c.status}
                    </span>

                    {c.status === 'PENDING' && (
                      <button
                        className="btn btn--secondary btn--sm"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        disabled={approveMut.isPending}
                        onClick={() => approveMut.mutate(c.consent_id)}
                      >
                        Grant
                      </button>
                    )}

                    {c.status === 'ACTIVE' && (
                      <button
                        className="btn btn--ghost btn--sm"
                        style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#ef4444' }}
                        disabled={revokeMut.isPending}
                        onClick={() => revokeMut.mutate(c.consent_id)}
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '1rem 0' }}>
              No simulated consents found in DB. Request one above!
            </p>
          )}
        </div>

        {/* Right Column: ULI & OCEN Explorer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {/* ULI Card */}
          <div className="sandbox-card">
            <h3 className="sandbox-card__title">
              <span role="img" aria-label="ULI">📥</span> ULI Standardized Fetch
            </h3>
            <p className="page-subtitle" style={{ fontSize: '0.85rem' }}>
              Simulate pulling standardized regulatory & cashflow packets from the ULI rails.
            </p>

            <div className="sandbox-form">
              <select
                className="sandbox-select"
                value={selectedMsmeULI}
                onChange={(e) => setSelectedMsmeULI(e.target.value)}
              >
                <option value="">-- Select MSME --</option>
                {msmesList.map((m) => (
                  <option key={m.msme_id} value={m.msme_id}>
                    {m.legal_name} ({m.msme_id})
                  </option>
                ))}
              </select>
              <button
                className="btn btn--primary btn--sm"
                disabled={!selectedMsmeULI || uliLoading}
                onClick={handleFetchULI}
              >
                {uliLoading ? 'Fetching…' : 'Fetch ULI Data'}
              </button>
            </div>

            {uliError && (
              <div className="sandbox-alert sandbox-alert--error">
                {uliError}
              </div>
            )}

            {uliPayload && (
              <div>
                <span className="sandbox-alert sandbox-alert--success" style={{ display: 'block', marginBottom: '8px' }}>
                  ✓ Standardized packet retrieved successfully.
                </span>
                <pre className="sandbox-payload">
                  {JSON.stringify(uliPayload, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* OCEN LSP Signals Card */}
          <div className="sandbox-card">
            <h3 className="sandbox-card__title">
              <span role="img" aria-label="OCEN">📡</span> OCEN LSP Signal Exchange
            </h3>
            <p className="page-subtitle" style={{ fontSize: '0.85rem' }}>
              Test loan offer calculations and LSP state negotiation signals.
            </p>

            <div className="sandbox-form">
              <select
                className="sandbox-select"
                value={selectedMsmeOCEN}
                onChange={(e) => setSelectedMsmeOCEN(e.target.value)}
              >
                <option value="">-- Select MSME --</option>
                {msmesList.map((m) => (
                  <option key={m.msme_id} value={m.msme_id}>
                    {m.legal_name} ({m.msme_id})
                  </option>
                ))}
              </select>
              <button
                className="btn btn--primary btn--sm"
                disabled={!selectedMsmeOCEN || ocenLoading}
                onClick={handleFetchOCEN}
              >
                {ocenLoading ? 'Negotiating…' : 'Get LSP Signal'}
              </button>
            </div>

            {ocenError && (
              <div className="sandbox-alert sandbox-alert--error">
                {ocenError}
              </div>
            )}

            {ocenPayload && (
              <div>
                <span className="sandbox-alert sandbox-alert--success" style={{ display: 'block', marginBottom: '8px' }}>
                  ✓ OCEN Signal Negotiation Complete.
                </span>
                <pre className="sandbox-payload">
                  {JSON.stringify(ocenPayload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
