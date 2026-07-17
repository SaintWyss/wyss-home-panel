# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-17)

**Core value:** Toda acción doméstica debe pasar por una única autoridad de política y ejecución de Wyss, conservar coherencia observable entre clientes y fallar de forma segura.
**Current focus:** Phase 1 — PR-00 Baseline reproducible y protección

## Current Position

Phase: 1 of 20 (PR-00 — Baseline reproducible y protección)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-07-17 — Roadmap v2.0.0 creado con cobertura completa y gates operativos explícitos.

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: Not enough data

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table and ADRs.

- Wyss remains the single authority for intent, policy, confirmation, execution and audit.
- Delivery follows PR-00 through PR-19 with v1 compatibility and verified rollback per increment.
- Hardware and external-service claims require evidence from the exact tested commit; missing evidence blocks completion.

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1 requires the exact panel, real light and verified factory backup for physical baseline evidence.
- Gates O-01..O-07 require explicit operator decisions at Phases 5, 8, 9/11, 12, 14, 15 and 20.
- Android, Spotify, Google Calendar, camera hardware and private remote network are external dependencies; simulations cannot close their physical criteria.
- Secure Boot, Flash Encryption and eFuses remain untouched without separate explicit authorization.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Future | MULTI-01, VOICE-03, MEDIA-03, PLUGIN-01 | Outside v2.0.0 | Initialization |

## Session Continuity

Last session: 2026-07-17
Stopped at: Roadmap and traceability initialized; Phase 1 is ready for planning.
Resume file: None
