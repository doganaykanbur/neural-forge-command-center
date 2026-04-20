# ARCHITECTURE.md — Distributed Auth API

## Goal: High-Performance Secure User Lifecycle

### 1. Technology Stack
- **Backend:** FastAPI (Python 3.12)
- **Database:** PostgreSQL (Core), Redis (Cache)
- **Security:** JWT (HMAC256), BCrypt hashing
- **Testing:** PyTest, coverage.py

### 2. Service Layout
- `auth_service`: Handle login, register, token refresh.
- `user_db`: Normalized schema for user profiles.
- `audit_logger`: Track security-sensitive actions.

### 3. Data Flow
`User Request` → `Global Validator` → `Orchestrator` → `Auth Service` → `Cache` → `DB`

### 4. Constraints
- Latency: <50ms for auth validation.
- Uptime: 99.9% target within Docker nodes.
