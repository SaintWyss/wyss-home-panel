---
phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
subsystem: projections
tags: [projection-store, reducers, multiclient, snapshots, deltas]
requires:
  - phase: 03-pr-02-identidad-pairing-y-event-backbone
    provides: identidad, event log y listener reanudable
provides:
  - Proyección SQLite materializada únicamente desde eventos
  - Reducer determinista con revisión y detección de huecos
  - Entrega multicliente por snapshot/deltas con fallback configurable
affects: [ui-shell, lights, conversation, integrations]
requirements-completed: [SYNC-02, SYNC-03]
requirements-partial: [SYNC-01]
completed-automated: 2026-07-17
---

# Phase 4: Projection Store and multiclient sync Summary

**La convergencia automatizada está completa; falta repetirla en PC, Android y panel físicos.**

## Accomplishments

- Materializó agregados desde el event log con orden global y revisión monotónica por agregado.
- Rechazó eventos atrasados o con huecos y volvió idempotentes los replays ya aplicados.
- Probó reconstrucciones independientes con snapshots byte-semánticamente equivalentes.
- Probó cambios originados en PC, Android y panel simulados convergiendo a la misma vista.
- Acotó cache de cursores e idempotency claims sin borrar eventos durables.
- Integró snapshots y deltas reales al listener v2, filtrando agregados internos del contrato público.
- Agregó `snapshot_fallback` reversible sin permitir escrituras autoritativas desde clientes.

## Commits

1. **Projection Store y reducer** - `dcdd1ac`
2. **Integración WebSocket v2** - `1f06d48`
3. **Idempotency cache acotado** - `d966e29`
4. **Convergencia por origen** - `4586a77`

## Physical Setup Pending

- Ejecutar un cambio desde PC, Android y panel reales sobre el mismo commit.
- Confirmar que las tres superficies convergen sin duplicación y guardar la evidencia.
- Esta prueba mantiene `SYNC-01` abierto; no fue reemplazada por simulación.
