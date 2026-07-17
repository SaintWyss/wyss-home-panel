---
phase: 03-pr-02-identidad-pairing-y-event-backbone
subsystem: identity-events
tags: [identity, revocation, websocket, sqlite, idempotency, resume]
requires:
  - phase: 02-pr-01-contratos-y-arquitectura-v2
    provides: ports y envelope v2 compartido
provides:
  - Identidad independiente por cliente con token hasheado, rotación y revocación
  - Event log revisionado, idempotente, correlacionado y reanudable
  - Listener v2 opt-in con snapshot/deltas y rollback conservando v1
affects: [projection-store, clients, remote-access, observability]
requirements-completed: [EVENT-01, EVENT-02, EVENT-03]
requirements-partial: [IDENT-01]
completed-automated: 2026-07-17
---

# Phase 3: Identity, pairing and event backbone Summary

**La parte automatizable está completa; falta demostrar revocación con un cliente físico real.**

## Accomplishments

- Persistió sólo SHA-256 de tokens por `client_id`, con capabilities allowlisted, generación,
  rotación y revocación releída en cada mensaje.
- Agregó CLI fail-closed para `pair`, `list`, `rotate` y `revoke`; `list` nunca expone token o hash.
- Implementó event log SQLite con revisión por agregado, cursor global, replay exacto,
  conflicto ante key reutilizada y orden correcto bajo concurrencia.
- Implementó heartbeat, rate limit acotado, correlation/causation y recuperación por snapshot o
  deltas posteriores a `last_event_id`.
- Registró `/v2/client` sólo con feature flag; al desactivarlo permanece `/v1/panel` y no se borran
  identidades ni eventos. Acciones no conectadas al funnel público de Wyss fallan cerradas.

## Commits

1. **Identidades revocables** - `fee1dcc`
2. **Event backbone reanudable** - `b21905d`
3. **Listener v2 y CLI operativa** - `8cd27c4`

## Physical Setup Pending

- Emparejar panel, Android o PC real con un token nuevo.
- Mantener la sesión abierta, ejecutar `revoke` y conservar evidencia de cierre `4403` sobre el
  mismo commit.
- Esta prueba no fue sustituida por simulación y mantiene `IDENT-01` abierto.
