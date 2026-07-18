---
phase: 19-pr-18-beta-diaria-y-soak
subsystem: resilience
tags: [soak, reconnect, idempotency, fault-injection, recovery]
provides:
  - Runner acelerado reproducible sobre servicios y stores reales
  - Evidencia exacta de 1000 reconnects, 500 brightness y 100 timers
  - Fallo de provider y reinicio de proceso con recuperación/dedupe
requirements-partial: [SOAK-01, SOAK-02]
completed-automated: 2026-07-18
---

# Phase 19: Beta diaria y soak Summary

**El alcance automatizable está cerrado; las 72 horas, la matriz física y la migración real siguen
bloqueando el cierre de la fase y del release.**

- `wyss-soak` compone los mismos servicios y stores SQLite del runtime, no réplicas simplificadas
  de su lógica de idempotencia o proyección.
- Una ejecución exacta completó 1.000 reconexiones, 500 cambios, 100 timers y 100 notificaciones
  en 1,626 s con 704 eventos, cero duplicados, cero estado fantasma y cero crashes.
- Se recrearon los servicios de luces y timers sobre los journals existentes; ninguna orden o
  notificación verificada fue ejecutada otra vez.
- Una caída inyectada del provider falló cerrada y la orden siguiente recuperó el estado normal.
- La suite completa quedó en 203 tests Python y 5 tests C++ aprobados.
- No se flasheó la placa, no se modificó NVS y la pantalla conserva el firmware funcional.
