import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  Toaster: () => null,
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

// Mock lucide-react icons
vi.mock('lucide-react', () => {
  const icons = [
    'LayoutDashboard', 'Server', 'History', 'FileText', 'Settings', 'LogOut',
    'Menu', 'X', 'ChevronDown', 'User', 'Plus', 'Edit', 'Trash2', 'RefreshCw',
    'Play', 'Loader2', 'Download', 'Search', 'MessageSquare', 'MoreVertical',
    'ArrowLeft', 'ArrowRight', 'Send', 'Copy', 'Check', 'Filter', 'AlertCircle', 'CheckCircle',
    'Activity', 'Clock', 'TrendingUp', 'Shield', 'Zap', 'Key', 'Moon', 'Sun',
    'Database', 'Globe', 'Bell'
  ]
  const mockIcon = (name: string) => ({ className }: { size: number; className?: string }) => (
    <svg data-testid={`icon-${name.toLowerCase()}`} className={className} />
  )
  return icons.reduce((acc, name) => ({ ...acc, [name]: mockIcon(name) }), {})
})

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({}),
    NavLink: ({ children, to, className, ...props }: any) => (
      <a href={to} className={typeof className === 'function' ? className({ isActive: false }) : className} {...props}>
        {children}
      </a>
    ),
    Outlet: () => <div data-testid="outlet" />,
  }
})

// Mock API client
vi.mock('@/api/client', () => ({
  api: {
    health: vi.fn().mockResolvedValue({ status: 'ok', version: '1.0.0', environment: 'development', demo_mode: true }),
    ready: vi.fn().mockResolvedValue({ status: 'ready', database: true, providers_loaded: 0, providers_healthy: 0 }),
    login: vi.fn().mockResolvedValue({ authorization_url: 'http://localhost:8080/auth', state: 'state', nonce: 'nonce', pkce_verifier: 'pkce' }),
    demoLogin: vi.fn().mockResolvedValue({ message: 'OK', user: { sub: 'demo-user', roles: ['operator'] } }),
    logout: vi.fn().mockResolvedValue({ logout_url: 'http://localhost:8080/logout' }),
    me: vi.fn().mockResolvedValue({ sub: 'demo-user', roles: ['operator'] }),
    listProviders: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }),
    createProvider: vi.fn().mockResolvedValue({ id: '1', name: 'Test', type: 'openai-compatible', base_url: 'https://api.com' }),
    updateProvider: vi.fn().mockResolvedValue({ id: '1', name: 'Test', type: 'openai-compatible', base_url: 'https://api.com' }),
    deleteProvider: vi.fn().mockResolvedValue(undefined),
    getProviderHealth: vi.fn().mockResolvedValue({ healthy: true }),
    testProvider: vi.fn().mockResolvedValue({ success: true, models: ['gpt-4o'] }),
    listSessions: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }),
    getSession: vi.fn().mockResolvedValue({ id: '1', title: 'Test', messages: [], message_count: 0 }),
    createSession: vi.fn().mockResolvedValue({ id: '1', title: 'Test' }),
    updateSession: vi.fn().mockResolvedValue({ id: '1', title: 'Updated' }),
    deleteSession: vi.fn().mockResolvedValue(undefined),
    addMessage: vi.fn().mockResolvedValue({ id: '1', role: 'user', content: 'Test' }),
    exportSession: vi.fn().mockResolvedValue(new Blob(['{}'], { type: 'application/json' })),
    listLogs: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, total_pages: 0 }),
    getLogStats: vi.fn().mockResolvedValue({ total_requests: 0, successful_requests: 0, failed_requests: 0, avg_latency_ms: 0, requests_by_provider: [], requests_by_status: [], error_rate: 0 }),
  },
}))