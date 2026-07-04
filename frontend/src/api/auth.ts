import apiClient from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
  role: string
  expires_in_seconds: number
}

export async function postLogin(
  username: string,
  role: 'bank_officer' | 'underwriter' | 'admin',
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/token', {
    username,
    role,
  })
  return data
}
