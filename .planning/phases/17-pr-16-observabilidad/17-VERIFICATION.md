---
phase: 17-pr-16-observabilidad
status: automated-observability-passed-physical-budgets-pending
verified_at: 2026-07-18T01:30:00Z
requirements: [OBS-01, OBS-02]
tested_commit: 8f70ddca69eec2aab755578e046be40e4889faff
---

# Verification: Phase 17

| Criterion | Evidence | Result |
|---|---|---|
| Reporte p50/p95/p99 y presupuestos | parser/SQLite y size automatizados; hardware declarado ausente | PASS PARTIAL + PHYSICAL PENDING |
| Métricas/traces sin secretos | redacción, cardinalidad y endpoint con capability | PASS AUTOMATED |
| Doctor/backpressure/cache/alertas | doctor, colas duras, retenciones y failure tests | PASS AUTOMATED |
| Runbook de aislamiento/rollback | procedimiento reproducible y flags no críticos | PASS AUTOMATED |

## Automated measurements

- Protocol parser, 10.000 muestras: p50 0,011450 ms; p95 0,015279 ms; p99 0,021854 ms.
- SQLite event append, 1.000 muestras: p50 0,242604 ms; p95 0,464130 ms; p99 0,834346 ms.
- Python: 186 tests PASS. CTest: 5/5 PASS.
- Firmware Phase 13: RAM 150.072 bytes (45,8 %), Flash 1.623.209 bytes (24,8 %), LVGL libre
  20.824 bytes. No hubo cambio de firmware en Phase 17.
- Endpoint: 403 sin `ops.read_metrics`; 200 con capability; headers/Authorization ausentes.
- Backpressure: límite 1 en fixture, segundo delta antes de ready cierra 4413 sin crecer.

## Metrics explicitly pending physical measurement

Tiempo real de arranque, FPS activo/reposo, heap/PSRAM en placa durante carga, tráfico idle/activo,
energía y temperatura. No se estiman ni se sustituyen con simulador.
