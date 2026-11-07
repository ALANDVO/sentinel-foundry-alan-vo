# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed
- Chat API: Added `metadata` field to `ChatRequest` dataclass in `backend/app/services/providers.py` to fix `TypeError` when calling Anthropic `/v1/messages` endpoint. The `convert_anthropic_to_internal` function was passing `metadata` but the dataclass didn't have the field.

## 1.1.0 — work-in-progress checkpoint

### Added
- Full multi-provider engine implementation in `backend/app/services/providers.py`:
  - BaseProvider abstract class with configurable retry logic, timeout handling, and streaming support
  - OpenAICompatibleProvider for OpenAI-compatible APIs (OpenAI, Azure OpenAI, local OpenAI-compatible servers)
  - AnthropicProvider for Anthropic Claude API with proper header formatting and message conversion
  - GeminiProvider for Google Gemini API with generation config and function calling support
  - OllamaProvider for local Ollama instances with options configuration
  - ProviderConfig, ChatMessage, ChatRequest, ChatResponse, StreamChunk data classes
  - ProviderError exception with status_code, provider, and retryable fields
  - create_provider factory function for dynamic provider instantiation
- Circuit breaker integration in ProviderRouter for automatic failover
- Request/response logging with error tracking

### Changed
- Replaced stub providers.py (single line "test") with complete implementation (~500 lines)

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-13

### Added
- Initial project structure with FastAPI backend and React frontend
- Docker Compose configuration with Keycloak, backend, frontend
- SQLite persistence for providers, request logs, and sessions
- OIDC authentication via Keycloak with PKCE
- Health and readiness endpoints
- Provider registry with basic CRUD API
- Request/response logging
- Basic React dashboard with provider management

### Security
- HttpOnly SameSite=Strict cookies for session management
- CSRF protection on state-changing operations
- Role-based access control (viewer, operator, admin)
- Demo mode explicitly gated and refused in production

---

Alan Vo · [alanvo.net](https://alanvo.net)
