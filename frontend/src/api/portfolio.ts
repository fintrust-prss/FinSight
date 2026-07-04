import apiClient from './client'

export type Tier =
  | 'Disciplined'
  | 'Moderately Disciplined'
  | 'Non-Disciplined'
  | 'No-Go'

export interface MSMESummary {
  msme_id: string
  legal_name: string
  udyam_number: string
  sector: string
  state: string
  latest_score: number | null
  tier: Tier
}

export interface TierDistribution {
  Disciplined: number
  'Moderately Disciplined': number
  'Non-Disciplined': number
  'No-Go': number
}

export interface PortfolioSummary {
  total_msmes: number
  tier_distribution: TierDistribution
  msmes: MSMESummary[]
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  const { data } = await apiClient.get<{ data: PortfolioSummary }>(
    '/portfolio/summary',
  )
  return data.data
}
