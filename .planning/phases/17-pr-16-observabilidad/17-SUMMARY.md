---
phase: 17-pr-16-observabilidad
subsystem: observability
tags: [metrics, percentiles, traces, health, backpressure]
provides:
  - Percentiles acotados y trazas correlacionadas sin contenido sensible
  - Health por módulo y exportación protegida por capacidad dedicada
  - Backpressure cerrado durante sincronización inicial
requirements-partial: [OBS-01, OBS-02]
completed-automated: 2026-07-18
---

# Phase 17: Observabilidad Summary

**Métricas, redacción, health, backpressure y runbook están verificados; los presupuestos que
dependen de instrumentos o de la placa quedan físicamente pendientes.**

- Retiene un máximo configurable de operaciones, muestras y traces; cardinalidad desconocida
  falla cerrada y cada deque descarta lo más antiguo.
- Calcula p50/p95/p99 y error count deterministas. Duraciones no finitas, negativas o absurdas se
  rechazan.
- Sólo conserva correlation IDs sintácticamente seguros. Contenido, headers y correlaciones
  sospechosas nunca se incorporan; se registra `redacted`.
- Exporta métricas únicamente cuando el feature flag está activo y la identidad posee
  `ops.read_metrics`; paneles ordinarios reciben 403.
- La cola de deltas mientras un cliente recibe snapshot tiene límite duro. Al saturarse, cierra la
  sesión con 4413 en lugar de agotar memoria o afectar clientes listos.
- El runbook define acceso, alertas, diagnóstico, aislamiento por feature flag y rollback que
  conserva luz/v1 como health básico.
