import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from '../pages/LoginPage'
import { AuthProvider } from '../hooks/useAuth'
import { ProviderStore } from '../hooks/useProviders'
import { SessionStore } from '../hooks/useSessions'
import { LogsStore } from '../hooks/useLogs'

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <ProviderStore>
          <SessionStore>
            <LogsStore>
              {component}
            </LogsStore>
          </SessionStore>
        </ProviderStore>
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('LoginPage', () => {
  it('renders login page with title', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText('Sentinel Foundry')).toBeInTheDocument()
    expect(screen.getByText('Multi-provider AI proxy for developer tools')).toBeInTheDocument()
  })

  it('has Keycloak login button', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByRole('button', { name: /sign in with keycloak/i })).toBeInTheDocument()
  })

  it('has demo login button', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByRole('button', { name: /demo mode/i })).toBeInTheDocument()
  })

  it('shows demo mode info', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText(/pre-configured with sample providers/i)).toBeInTheDocument()
    expect(screen.getByText(/full dashboard access with operator role/i)).toBeInTheDocument()
  })
})