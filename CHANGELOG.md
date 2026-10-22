# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

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