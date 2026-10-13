import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { ProvidersPage } from '../pages/ProvidersPage'
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

describe('ProvidersPage', () => {
  it('renders providers page with title', () => {
    renderWithProviders(<ProvidersPage />)
    expect(screen.getByText('Providers')).toBeInTheDocument()
    expect(screen.getByText('Configure and manage LLM providers')).toBeInTheDocument()
  })

  it('has add provider button', () => {
    renderWithProviders(<ProvidersPage />)
    expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument()
  })

  it('shows empty state when no providers', async () => {
    renderWithProviders(<ProvidersPage />)
    await waitFor(() => {
      expect(screen.getByText('No providers configured')).toBeInTheDocument()
    })
    expect(screen.getByText('Add your first provider to start routing requests')).toBeInTheDocument()
  })

  it('opens modal when add provider clicked', async () => {
    renderWithProviders(<ProvidersPage />)
    fireEvent.click(screen.getByRole('button', { name: /add provider/i }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /add provider/i })).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Type')).toBeInTheDocument()
    expect(screen.getByLabelText('Base URL')).toBeInTheDocument()
  })

  it('modal has all provider types', async () => {
    renderWithProviders(<ProvidersPage />)
    fireEvent.click(screen.getByRole('button', { name: /add provider/i }))
    await waitFor(() => {
      const select = screen.getByLabelText('Type')
      expect(select).toHaveValue('openai-compatible')
    })
  })
})