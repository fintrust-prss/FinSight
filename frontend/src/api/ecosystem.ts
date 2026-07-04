import apiClient from './client'

export interface ConnectorStatus {
  connector_id: string
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE'
  ping_latency_ms: number
  connected_since: string
  last_heartbeat: string
}

export interface AAConsent {
  consent_id: string
  msme_id: string
  data_types: string[]
  purpose: string
  status: 'PENDING' | 'ACTIVE' | 'REVOKED' | 'EXPIRED'
  expiry: string
}

export interface ULIDataResponse {
  uli_reference_id: string
  fetched_at: string
  schema_version: string
  consent_reference: string
  msme_profile: {
    msme_id: string
    regulatory_filings: {
      udyam_registration: {
        status: string
        date_of_registration: string
      }
      gst_status: {
        registration_state: string
        active_status: boolean
        filing_frequency: string
      }
    }
    financial_aggregates_last_12m: {
      estimated_gst_turnover_inr: number
      avg_monthly_bank_balance_inr: number
      upi_transaction_count: number
      utility_bill_payment_on_time_ratio: number
    }
  }
}

export interface OCENSignalResponse {
  ocen_tx_id: string
  timestamp: string
  lsp_identifier: string
  msme_id: string
  credit_score_evaluated: number
  eligibility_status: 'APPROVED' | 'REJECTED'
  signal_payload?: {
    offer_id: string
    max_principal_amount: number
    interest_rate_apr: number
    tenure_months: number
    repayment_frequency: string
  }
  exchange_status: string
  message: string
}

export async function fetchULIStatus(): Promise<ConnectorStatus> {
  const { data } = await apiClient.get<{ data: ConnectorStatus }>(
    '/ecosystem/uli/status',
  )
  return data.data
}

export async function fetchOCENStatus(): Promise<ConnectorStatus> {
  const { data } = await apiClient.get<{ data: ConnectorStatus }>(
    '/ecosystem/ocen/status',
  )
  return data.data
}

export async function initiateAAConsent(
  msmeId: string,
  validHours = 24,
): Promise<{ consent_id: string; redirect_url: string; status: string }> {
  const { data } = await apiClient.post<{ data: { consent_id: string; redirect_url: string; status: string } }>(
    '/ecosystem/aa/request',
    {
      msme_id: msmeId,
      valid_hours: validHours,
    },
  )
  return data.data
}

export async function fetchPendingConsents(): Promise<AAConsent[]> {
  const { data } = await apiClient.get<{ data: AAConsent[] }>(
    '/ecosystem/aa/pending',
  )
  return data.data
}

export async function approveAAConsent(
  consentId: string,
): Promise<{ consent_id: string; status: string }> {
  const { data } = await apiClient.post<{ data: { consent_id: string; status: string } }>(
    `/ecosystem/aa/approve/${consentId}`,
  )
  return data.data
}

export async function revokeAAConsent(
  consentId: string,
): Promise<{ consent_id: string; status: string }> {
  const { data } = await apiClient.post<{ data: { consent_id: string; status: string } }>(
    `/ecosystem/aa/revoke/${consentId}`,
  )
  return data.data
}

export async function fetchULIData(msmeId: string): Promise<ULIDataResponse> {
  const { data } = await apiClient.get<{ data: ULIDataResponse }>(
    `/ecosystem/uli/fetch/${msmeId}`,
  )
  return data.data
}

export async function fetchOCENSignal(msmeId: string): Promise<OCENSignalResponse> {
  const { data } = await apiClient.get<{ data: OCENSignalResponse }>(
    `/ecosystem/ocen/lsp-signal/${msmeId}`,
  )
  return data.data
}
