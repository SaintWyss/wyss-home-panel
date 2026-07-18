---
phase: 12-pr-11-recordatorios-notificaciones
subsystem: reminders
tags: [reminders, notifications, outbox, projection, lvgl]
requires:
  - phase: 07-pr-06-conversacion-visual-y-confirmaciones
    provides: planes, policy, confirmacion y ejecucion exclusiva en Wyss
provides:
  - Proyeccion sanitizada y durable de recordatorios autoritativos en Wyss
  - Outbox de notificaciones idempotente, recuperable y con deep links
  - Estado coherente en PC, Android y panel, incluido modo reposo
requirements-partial: [REM-01, REM-02]
completed-automated: 2026-07-18
---

# Phase 12: Recordatorios y notificaciones Summary

**Backend, persistencia, proyección y firmware están verificados; O-04 y Android físico siguen
siendo gates externos.**

## Accomplishments

- Mantiene recordatorios, recurrencia, completar y posponer bajo autoridad exclusiva de Wyss.
  Home Edge sólo consulta un snapshot interno autenticado y no expone tokens ni scheduler propio.
- Valida estrictamente timezone, vencimiento con offset, estado, revisión, recurrencia y campos;
  rechaza secretos o extensiones inesperadas y acota la proyección enviada a clientes.
- Conserva snapshot y revisión en SQLite privado, sobrevive reinicios y publica cache stale sin
  inventar disponibilidad cuando Wyss falla.
- Persiste notificaciones en un outbox privado por ID determinista. Permisos/proveedor no
  disponibles dejan el item pendiente; una entrega aceptada se registra una sola vez y no borra
  el recordatorio.
- Desactivar push conserva cache y outbox. Volver a habilitar entrega reanuda los pendientes sin
  duplicarlos; el deep link `wyss://reminders/<id>` apunta al recordatorio sanitizado.
- Obliga crear, completar y posponer a atravesar intención, plan B/C, policy y confirmación Wyss;
  Home Edge no ofrece CRUD directo.
- PC, Android y panel reciben la misma proyección con una sola consulta. El panel muestra cantidad
  y próximo recordatorio en Agenda y en reposo, sin seleccionar un mecanismo Android antes O-04.

## Remaining External Gates

O-04 debe elegir y registrar el mecanismo Android después de probar background, permisos,
deduplicación y deep links en un teléfono real. Luego Wyss real debe demostrar creación,
recurrencia, completar/posponer y pérdida/recuperación de conectividad. REM-01 y REM-02 permanecen
abiertos hasta esa evidencia.
