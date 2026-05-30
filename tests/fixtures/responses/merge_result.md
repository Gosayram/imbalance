# Auth Decisions - Merged

## Database Choice
- **Decision**: Use PostgreSQL 17
- **Rationale**: JSONB for flexible schema, native FTS, team experience
- **Alternatives considered**: MySQL (rejected: no JSONB), MongoDB (rejected: no transactions)
- **Confirmed by**: 12 sessions

## Authentication
- **Decision**: JWT with refresh token rotation
- **Rationale**: Stateless, works across microservices, industry standard
- **Implementation**: Pessimistic lock on refresh_tokens table
- **Confirmed by**: 8 sessions
