# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-proxy-skeleton

## Roadmap

### core-proxy-skeleton — Core proxy skeleton with FastAPI backend and React frontend

Status: done

Acceptance:
- FastAPI app starts and serves health endpoint
- React frontend builds and serves dashboard
- Docker compose runs backend, frontend, and Keycloak
- Basic OIDC login flow works
- SQLite persistence for provider configs and request logs

Implementation: `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/api/auth.py`, `backend/app/api/providers.py`, `backend/app/api/chat.py`, `backend/app/api/sessions.py`, `backend/app/api/logs.py`, `backend/app/services/providers.py`, `backend/app/services/router.py`, `backend/app/models/__init__.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/security.py`, `backend/app/core/auth.py`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/pages/ProvidersPage.tsx`, `frontend/src/pages/SessionsPage.tsx`, `frontend/src/pages/SessionDetailPage.tsx`, `frontend/src/pages/LogsPage.tsx`, `frontend/src/pages/SettingsPage.tsx`, `frontend/src/hooks/useAuth.tsx`, `frontend/src/hooks/useProviders.tsx`, `frontend/src/hooks/useSessions.tsx`, `frontend/src/hooks/useLogs.tsx`, `frontend/src/api/client.ts`, `frontend/src/types/index.ts`, `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/requirements.txt`, `frontend/package.json`

Tests: `backend/tests/test_health.py`, `backend/tests/test_auth.py`, `backend/tests/test_providers.py`, `backend/tests/test_sessions.py`, `backend/tests/test_logs.py`, `backend/tests/test_chat.py`, `backend/tests/test_models.py`, `backend/tests/test_services.py`, `frontend/src/__tests__/LoginPage.test.tsx`, `frontend/src/__tests__/DashboardPage.test.tsx`, `frontend/src/__tests__/ProvidersPage.test.tsx`

### multi-provider-engine — Multi-provider request routing with health monitoring

Status: done

Acceptance:
- OpenAI-compatible, Anthropic, Gemini, Ollama adapters
- Provider health checks and automatic failover
- Request/response validation and transformation
- Circuit breaker for failing providers

Implementation: `backend/app/services/providers.py`, `backend/app/services/router.py`, `backend/app/api/providers.py`

Tests: `backend/tests/test_services.py`, `backend/tests/test_providers.py`

### claude-code-compatibility — Claude Code API compatibility layer

Status: done

Acceptance:
- Implements /v1/messages endpoint for Anthropic format
- Handles beta headers and streaming
- Converts between Anthropic and provider formats

Implementation: `backend/app/api/chat.py`

Tests: `backend/tests/test_chat.py`

### provider-management-ui — Provider configuration and monitoring dashboard

Status: done

Acceptance:
- Add/edit/delete provider configurations
- Real-time health status display
- Request log viewer with filtering

Implementation: `frontend/src/pages/ProvidersPage.tsx`, `frontend/src/pages/LogsPage.tsx`, `frontend/src/hooks/useProviders.tsx`, `frontend/src/hooks/useLogs.tsx`

Tests: `frontend/src/__tests__/ProvidersPage.test.tsx`

### session-persistence — Session management and conversation history

Status: done

Acceptance:
- Persist conversations to SQLite
- Resume conversations across restarts
- Export/import conversation data

Implementation: `backend/app/api/sessions.py`, `backend/app/models/__init__.py`, `frontend/src/pages/SessionsPage.tsx`, `frontend/src/pages/SessionDetailPage.tsx`, `frontend/src/hooks/useSessions.tsx`

Tests: `backend/tests/test_sessions.py`

