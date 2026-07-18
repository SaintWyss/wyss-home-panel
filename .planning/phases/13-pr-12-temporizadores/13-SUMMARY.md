---
phase: 13-pr-12-temporizadores
subsystem: timers
tags: [timers, deadlines, idempotency, notifications, lvgl]
requires:
  - phase: 12-pr-11-recordatorios-notificaciones
    provides: entrega durable e idempotente de notificaciones
provides:
  - Proyeccion durable de timers y presets autoritativos en Wyss
  - Finalizacion exactamente una vez con dedupe persistente
  - Exportacion/importacion segura para rollback de scheduler
requirements-partial: [TIMER-01, TIMER-02]
completed-automated: 2026-07-18
---

# Phase 13: Temporizadores Summary

**Scheduler contract, persistencia, finalización, proyección y firmware están verificados; Wyss y
Android reales siguen siendo evidencia externa.**

## Accomplishments

- Wyss conserva el reloj monotónico, deadline y scheduler autoritativos. Home Edge consulta un
  snapshot interno estricto; no decrementa timers ni ejecuta un scheduler paralelo.
- Valida estados running/paused/cancelled/completed, revisión, duración, remaining, deadline con
  offset, preset e identidades de finalización/notificación sin exponer autenticación.
- Separa reloj monotónico para programar refresh del reloj civil usado para antigüedad: atrasar o
  adelantar el reloj del host no posterga la recuperación del estado autoritativo.
- Persiste snapshots privados, dedupe durable por `completion_id` y outbox de notificación. Cada
  finalización publica un único `timer.completed`; reintentos y reinicios no duplican.
- Exporta sólo timers running/paused e importa conservando ID, deadline, remaining, preset, estado
  y revisión para rollback al scheduler anterior.
- Crear, pausar, reanudar, cancelar y usar presets atraviesa intención, plan, policy y confirmación
  Wyss; no hay endpoint rápido que omita autoridad.
- PC, Android y panel reciben el mismo deadline revisionado con una consulta. El panel muestra el
  timer más próximo y remaining en Agenda y reposo.

## Remaining External Gates

Wyss real debe demostrar el scheduler monotónico y operaciones desde tres superficies sobre el
mismo commit. Android físico debe recibir una sola notificación por vencimiento. TIMER-01 y
TIMER-02 permanecen abiertos hasta esa evidencia.
