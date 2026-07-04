import apiClient from './client'
import type { Tier } from './portfolio'

// ─── Profile ─────────────────────────────────────────────────────────────────

export interface MSMEProfile {
  id: number
  msme_id: string
  legal_name: string
  udyam_number: string
  sector: string
  sub_sector: string
  vintage_years: number
  state: string
  registration_type: string
  created_at: string | null
}

export async function fetchMSMEProfile(msmeId: string): Promise<MSMEProfile> {
  const { data } = await apiClient.get<{ data: MSMEProfile }>(`/msme/${msmeId}`)
  return data.data
}

// ─── Score ────────────────────────────────────────────────────────────────────

export interface ScoreData {
  msme_id: string
  overall_score: number
  tier: Tier
  as_of_date: string
  dimension_scores: Record<string, number>
  model_version: string
}

export async function fetchMSMEScore(
  msmeId: string,
  bankProfile = 'idbi',
): Promise<ScoreData> {
  const { data } = await apiClient.get<{ data: ScoreData }>(
    `/msme/${msmeId}/score`,
    { params: { bank_profile: bankProfile } },
  )
  return data.data
}

// ─── Score History ────────────────────────────────────────────────────────────

export interface ScoreHistoryPoint {
  as_of_date: string
  overall_score: number
  tier: Tier
  dimension_scores: Record<string, number>
}

export async function fetchMSMEHistory(
  msmeId: string,
  limit = 12,
): Promise<ScoreHistoryPoint[]> {
  const { data } = await apiClient.get<{
    data: { msme_id: string; history: ScoreHistoryPoint[] }
  }>(`/msme/${msmeId}/score/history`, { params: { limit } })
  return data.data.history
}

// ─── Explain ──────────────────────────────────────────────────────────────────

export interface ExplainData {
  msme_id: string
  shap_summary: Record<string, number>
  reasons: Record<string, string[]>
}

export async function fetchMSMEExplain(
  msmeId: string,
  bankProfile = 'idbi',
): Promise<ExplainData> {
  const { data } = await apiClient.get<{ data: ExplainData }>(
    `/msme/${msmeId}/explain`,
    { params: { bank_profile: bankProfile } },
  )
  return data.data
}

// ─── Data Sources ─────────────────────────────────────────────────────────────

export interface DataSourcesData {
  msme_id: string
  connected_sources: string[]
  consent_count: number
}

export async function fetchDataSources(msmeId: string): Promise<DataSourcesData> {
  const { data } = await apiClient.get<{ data: DataSourcesData }>(
    `/msme/${msmeId}/data-sources`,
  )
  return data.data
}

// ─── Consent ──────────────────────────────────────────────────────────────────

export interface ConsentData {
  consent_id: string
  msme_id: string
  data_types: string[]
  purpose: string
  status: string
  expiry: string
}

export async function postConsent(msmeId: string): Promise<ConsentData> {
  const { data } = await apiClient.post<{ data: ConsentData }>('/consent', {
    msme_id: msmeId,
    data_types: ['gst', 'upi', 'bank_statement', 'epfo', 'utility', 'digital_footprint'],
    purpose: 'Credit Scoring Assessment',
    valid_hours: 24,
  })
  return data.data
}

// ─── Rescore ──────────────────────────────────────────────────────────────────

export async function postRescore(msmeId: string): Promise<void> {
  await apiClient.post(`/msme/${msmeId}/rescore`)
}
