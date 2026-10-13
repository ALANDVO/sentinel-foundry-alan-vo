import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { DashboardPage } from '../pages/DashboardPage'
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

describe('DashboardPage', () => {
  it('renders dashboard with stats cards', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Overview of provider health and system status')).toBeInTheDocument()
    expect(screen.getByText('Total Providers')).toBeInTheDocument()
    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('Circuit Open')).toBeInTheDocument()
    expect(screen.getByText('Unhealthy')).toBeInTheDocument()
  })

  it('shows provider table when providers loaded', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Providers')).toBeInTheDocument()
  })

  it('shows quick actions', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /add provider/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view sessions/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view logs/i })).toBeInTheDocument()
  })

  it('shows system info', () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText('System Info')).toBeInTheDocument()
    expect(screen.getByText('Environment')).toBeInTheDocument()
    expect(screen.getByText('Version')).toBeInTheDocument()
  })
})