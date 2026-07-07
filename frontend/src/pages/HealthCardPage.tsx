import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  RadialBarChart,
  RadialBar,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import {
  fetchMSMEProfile,
  fetchMSMEScore,
  // fetchMSMEExplain,
  fetchMSMEHistory,
  postConsent,
} from '../api/msme'
import TierBadge, { tierHex } from '../components/TierBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { ErrorCard } from '../components/ErrorBoundary'

/* ─── human-readable dimension labels ──────────────────────────────────────── */
const DIM_LABELS: Record<string, string> = {
  revenue_cashflow: 'Revenue & Cash Flow',
  compliance_formalization: 'Compliance',
  repayment_creditworthiness: 'Repayment',
  operational_stability: 'Operational Stability',
  workforce_employment: 'Workforce',
  digital_ecosystem: 'Digital Footprint',
  bureau_credit_history: 'Credit History',
}

function dimLabel(key: string): string {
  return DIM_LABELS[key] ?? key.replace(/_/g, ' ')
}

/* ─── colour for SHAP bars (kept commented for future restoration) ───────────── */
/*
function shapColor(val: number) {
  return val >= 0 ? '#10b981' : '#ef4444'
}
*/

export default function HealthCardPage() {
  const { id: msmeId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  // const [consentGranted, setConsentGranted] = useState(false)
  const [activeTab, setActiveTab] = useState<'radar' | 'gauge' | 'shap'>('radar')

  /* ── Profile ── */
  const profileQ = useQuery({
    queryKey: ['msme-profile', msmeId],
    queryFn: () => fetchMSMEProfile(msmeId!),
    enabled: !!msmeId,
  })

  /* ── Score ── */
  const scoreQ = useQuery({
    queryKey: ['msme-score', msmeId],
    queryFn: () => fetchMSMEScore(msmeId!),
    enabled: !!msmeId,
    retry: (count, err: any) => {
      // don't retry on 403 consent gate
      if (err?.response?.status === 403) return false
      return count < 2
    },
  })

  /* ── Explain (kept commented for future SHAP restoration) ── */
  /*
  const explainQ = useQuery({
    queryKey: ['msme-explain', msmeId],
    queryFn: () => fetchMSMEExplain(msmeId!),
    enabled: !!msmeId && (scoreQ.isSuccess || consentGranted),
    retry: false,
  })
  */

  /* ── History ── */
  const historyQ = useQuery({
    queryKey: ['msme-history', msmeId],
    queryFn: () => fetchMSMEHistory(msmeId!, 6),
    enabled: !!msmeId,
    retry: false,
  })

  /* ── Consent mutation ── */
  const consentMut = useMutation({
    mutationFn: () => postConsent(msmeId!),
    onSuccess: () => {
      // setConsentGranted(true)
      qc.invalidateQueries({ queryKey: ['msme-score', msmeId] })
      qc.invalidateQueries({ queryKey: ['msme-explain', msmeId] })
    },
  })

  /* ── Loading / error ── */
  if (profileQ.isLoading)
    return <LoadingSpinner variant="full" label="Loading MSME profile…" />
  if (profileQ.isError)
    return (
      <div className="page-error">
        <ErrorCard
          title="Failed to load MSME"
          message={(profileQ.error as any)?.message}
          onRetry={() => profileQ.refetch()}
        />
      </div>
    )

  const profile = profileQ.data!
  const needsConsent = scoreQ.error && (scoreQ.error as any)?.response?.status === 403

  /* ── Radar data ── */
  const radarData = scoreQ.data
    ? Object.entries(scoreQ.data.dimension_scores).map(([key, value]) => ({
        dimension: dimLabel(key),
        score: Math.round(value),
        fullMark: 100,
      }))
    : []

  /* ── Gauge data ── */
  const overallScore = scoreQ.data?.overall_score ?? 0
  const gaugeData = [{ name: 'score', value: overallScore }]

  /* ── SHAP data (kept commented for future restoration) ── */
  /*
  const shapData = explainQ.data
    ? Object.entries(explainQ.data.shap_summary)
        .map(([key, value]) => ({
          name: dimLabel(key),
          value: Number(value.toFixed(3)),
        }))
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 8)
    : []
  */

  const tier = scoreQ.data?.tier ?? 'Non-Disciplined'
  const tierColor = tierHex(tier)

  return (
    <div className="health-card-page">
      {/* ── Breadcrumb ── */}
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/dashboard" className="breadcrumb__link">
          Dashboard
        </Link>
        <span className="breadcrumb__sep" aria-hidden="true">/</span>
        <span className="breadcrumb__current">{profile.legal_name}</span>
      </nav>

      {/* ── Profile Header ── */}
      <div className="profile-header">
        <div className="profile-header__info">
          <h1 className="profile-header__name">{profile.legal_name}</h1>
          <div className="profile-header__meta">
            <span className="meta-pill">
              <span className="meta-pill__icon" aria-hidden="true">📋</span>
              {profile.udyam_number}
            </span>
            <span className="meta-pill">
              <span className="meta-pill__icon" aria-hidden="true">🏭</span>
              {profile.sector.charAt(0).toUpperCase() + profile.sector.slice(1)} ·{' '}
              {profile.sub_sector.replace(/_/g, ' ')}
            </span>
            <span className="meta-pill">
              <span className="meta-pill__icon" aria-hidden="true">📍</span>
              {profile.state}
            </span>
            <span className="meta-pill">
              <span className="meta-pill__icon" aria-hidden="true">⏱</span>
              {profile.vintage_years}y vintage
            </span>
          </div>
        </div>
        <div className="profile-header__actions">
          <Link
            to={`/msme/${msmeId}/data`}
            id="btn-data-sources"
            className="btn btn--secondary btn--sm"
          >
            Data Sources
          </Link>
        </div>
      </div>

      {/* ── Consent Gate ── */}
      {needsConsent && (
        <div className="consent-gate" role="alert">
          <div className="consent-gate__icon" aria-hidden="true">🔒</div>
          <div>
            <h3 className="consent-gate__title">Account Aggregator Consent Required</h3>
            <p className="consent-gate__desc">
              Scoring alternate data requires consent from the MSME's Account
              Aggregator. Grant a 24-hour consent token to proceed.
            </p>
          </div>
          <button
            id="btn-grant-consent"
            className="btn btn--primary"
            disabled={consentMut.isPending}
            onClick={() => consentMut.mutate()}
          >
            {consentMut.isPending ? (
              <>
                <span className="btn-spinner" aria-hidden="true" /> Granting…
              </>
            ) : (
              'Grant AA Consent'
            )}
          </button>
        </div>
      )}

      {/* ── Score Band ── */}
      {scoreQ.isLoading && (
        <div className="score-band score-band--loading">
          <LoadingSpinner label="Computing score…" />
        </div>
      )}

      {scoreQ.isSuccess && (
        <div className="score-band" style={{ '--tier-accent': tierColor } as React.CSSProperties}>
          <div className="score-band__main">
            <div className="score-band__number" aria-label={`Overall score: ${overallScore.toFixed(1)}`}>
              {overallScore.toFixed(1)}
              <span className="score-band__denom">/100</span>
            </div>
            <div className="score-band__meta">
              <TierBadge tier={tier} />
              <span className="score-band__date">as of {scoreQ.data.as_of_date}</span>
              <span className="score-band__model">{scoreQ.data.model_version}</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Charts Section ── */}
      {scoreQ.isSuccess && (
        <div className="charts-section">
          {/* Tab selector */}
          <div className="chart-tabs" role="tablist" aria-label="Chart view">
            {(['radar', 'gauge', 'shap'] as const).map((tab) => (
              <button
                key={tab}
                id={`tab-${tab}`}
                role="tab"
                aria-selected={activeTab === tab}
                className={`chart-tab${activeTab === tab ? ' chart-tab--active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'radar' && '◎ Radar'}
                {tab === 'gauge' && '◐ Gauge'}
                {/* {tab === 'shap' && '✦ Why This Score'} */}
              </button>
            ))}
          </div>

          {/* ── Radar Chart ── */}
          {activeTab === 'radar' && (
            <div className="chart-panel" role="tabpanel" aria-labelledby="tab-radar">
              <h2 className="chart-title">7-Dimension Health Radar</h2>
              <div className="chart-wrap chart-wrap--radar" aria-label="Radar chart showing 7 health dimensions">
                <ResponsiveContainer width="100%" height={380}>
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                    <PolarGrid stroke="rgba(255,255,255,0.08)" />
                    <PolarAngleAxis
                      dataKey="dimension"
                      tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'Inter' }}
                    />
                    <PolarRadiusAxis
                      angle={30}
                      domain={[0, 100]}
                      tick={{ fill: '#475569', fontSize: 10 }}
                      tickCount={5}
                    />
                    <Radar
                      name="Score"
                      dataKey="score"
                      stroke={tierColor}
                      fill={tierColor}
                      fillOpacity={0.22}
                      strokeWidth={2}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#111827',
                        border: '1px solid #1e2d45',
                        borderRadius: '8px',
                        color: '#f1f5f9',
                        fontFamily: 'Inter',
                        fontSize: 13,
                      }}
                      formatter={(val: number) => [`${val}/100`, 'Score']}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Dimension score pills */}
              <div className="dim-grid">
                {Object.entries(scoreQ.data.dimension_scores).map(([key, val]) => (
                  <div key={key} className="dim-card">
                    <div className="dim-card__label">{dimLabel(key)}</div>
                    <div className="dim-card__bar-wrap">
                      <div
                        className="dim-card__bar"
                        style={{
                          width: `${val}%`,
                          background: tierColor,
                        }}
                        role="progressbar"
                        aria-valuenow={Math.round(val)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${dimLabel(key)}: ${Math.round(val)}`}
                      />
                    </div>
                    <div className="dim-card__score">{Math.round(val)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Gauge Chart ── */}
          {activeTab === 'gauge' && (
            <div className="chart-panel" role="tabpanel" aria-labelledby="tab-gauge">
              <h2 className="chart-title">Overall Health Score</h2>
              <div
                className="chart-wrap chart-wrap--gauge"
                aria-label={`Gauge showing overall score of ${overallScore.toFixed(1)} out of 100`}
              >
                <ResponsiveContainer width="100%" height={340}>
                  <RadialBarChart
                    cx="50%"
                    cy="60%"
                    innerRadius="60%"
                    outerRadius="90%"
                    barSize={20}
                    data={gaugeData}
                    startAngle={180}
                    endAngle={0}
                  >
                    <RadialBar
                      background={{ fill: 'rgba(255,255,255,0.04)' }}
                      dataKey="value"
                      cornerRadius={10}
                    >
                      <Cell fill={tierColor} />
                    </RadialBar>
                    <text
                      x="50%"
                      y="58%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#f1f5f9"
                      fontSize="2.5rem"
                      fontWeight={800}
                      fontFamily="Inter"
                    >
                      {overallScore.toFixed(0)}
                    </text>
                    <text
                      x="50%"
                      y="72%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#94a3b8"
                      fontSize="0.875rem"
                      fontFamily="Inter"
                    >
                      out of 100
                    </text>
                  </RadialBarChart>
                </ResponsiveContainer>

                {/* Tier strip */}
                <div className="gauge-tier-strip">
                  {[
                    { range: '0–40', label: 'No-Go', color: '#ef4444' },
                    { range: '40–60', label: 'Non-Disciplined', color: '#f97316' },
                    { range: '60–75', label: 'Moderate', color: '#f59e0b' },
                    { range: '75–100', label: 'Disciplined', color: '#10b981' },
                  ].map((t) => (
                    <div key={t.label} className="gauge-tier-item">
                      <span
                        className="gauge-tier-dot"
                        style={{ background: t.color }}
                      />
                      <span className="gauge-tier-range">{t.range}</span>
                      <span className="gauge-tier-label">{t.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── SHAP / Why This Score ── */}
          {/* {activeTab === 'shap' && (
            <div className="chart-panel" role="tabpanel" aria-labelledby="tab-shap">
              <h2 className="chart-title">Why This Score?</h2>
              <p className="chart-subtitle">
                SHAP feature contributions — positive values push the score up, negative
                values push it down.
              </p>

              {explainQ.isLoading && <LoadingSpinner label="Loading explanation…" />}
              {explainQ.isError && (
                <ErrorCard
                  title="Explanation unavailable"
                  message="Could not load SHAP data."
                  onRetry={() => explainQ.refetch()}
                />
              )}

              {shapData.length > 0 && (
                <div
                  className="chart-wrap chart-wrap--shap"
                  aria-label="Bar chart showing SHAP feature contributions"
                >
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart
                      data={shapData}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <XAxis
                        type="number"
                        tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'Inter' }}
                        axisLine={{ stroke: '#1e2d45' }}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={160}
                        tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'Inter' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#111827',
                          border: '1px solid #1e2d45',
                          borderRadius: '8px',
                          color: '#f1f5f9',
                          fontSize: 12,
                          fontFamily: 'Inter',
                        }}
                        formatter={(val: number) => [
                          `${val > 0 ? '+' : ''}${val.toFixed(3)}`,
                          'SHAP value',
                        ]}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {shapData.map((entry, i) => (
                          <Cell key={i} fill={shapColor(entry.value)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )} */}
        </div>
      )}

      {/* ── Score History Sparkline ── */}
      {historyQ.isSuccess && historyQ.data.length > 1 && (
        <div className="history-section">
          <h2 className="section-title">Score History</h2>
          <div className="history-list">
            {[...historyQ.data].reverse().map((h, i) => (
              <div key={i} className="history-item">
                <span className="history-item__date">{h.as_of_date}</span>
                <div className="history-item__bar-wrap">
                  <div
                    className="history-item__bar"
                    style={{
                      width: `${h.overall_score}%`,
                      background: tierHex(h.tier),
                    }}
                  />
                </div>
                <span className="history-item__score">{h.overall_score.toFixed(1)}</span>
                <TierBadge tier={h.tier} compact />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
