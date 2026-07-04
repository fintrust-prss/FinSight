/**
 * Axios API client — auto-attaches JWT Bearer token from localStorage.
 * All requests are relative to /api/v1 (proxied by Vite to the FastAPI backend).
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : '/api/v1'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// Attach Authorization header on every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('fs_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global 401 handler — clear token and reload to login
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('fs_token')
      localStorage.removeItem('fs_role')
      localStorage.removeItem('fs_username')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default apiClient
