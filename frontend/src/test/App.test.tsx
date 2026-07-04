import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

function renderApp(initialPath = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('App routing — Phase 0 scaffold', () => {
  it('redirects root / to /dashboard', () => {
    renderApp('/')
    expect(screen.getByText(/Portfolio Dashboard/i)).toBeDefined()
  })

  it('renders login page at /login', () => {
    renderApp('/login')
    expect(screen.getByText(/Login/i)).toBeDefined()
  })

  it('renders health card placeholder at /msme/123', () => {
    renderApp('/msme/123')
    expect(screen.getByText(/MSME Health Card/i)).toBeDefined()
  })

  it('renders ecosystem page at /ecosystem', () => {
    renderApp('/ecosystem')
    expect(screen.getByText(/Ecosystem Status/i)).toBeDefined()
  })

  it('renders 404 for unknown routes', () => {
    renderApp('/this-route-does-not-exist')
    expect(screen.getByText(/404/i)).toBeDefined()
  })

  it('shows Phase 0 Scaffold badge on placeholder pages', () => {
    renderApp('/dashboard')
    expect(screen.getByText(/Phase 0 Scaffold/i)).toBeDefined()
  })
})
