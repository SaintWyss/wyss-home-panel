---
phase: 11-pr-10-google-calendar
subsystem: calendar
tags: [google-calendar, incremental-sync, projection, lvgl, policy]
requires:
  - phase: 07-pr-06-conversacion-visual-y-confirmaciones
    provides: planes, policy, confirmacion y ejecucion exclusiva en Wyss
provides:
  - Agenda semanal sanitizada y consistente entre PC, Android y panel
  - Sync incremental durable con paginacion, recurrencia, all-day y resync
  - Scopes exactos separados y cache explicita al revocar escritura
requirements-partial: [CAL-01, CAL-02]
completed-automated: 2026-07-18
---

# Phase 11: Google Calendar Summary

**Backend, política, proyección, UI y arranque del panel están verificados; O-07 y una cuenta
Calendar real siguen siendo gates externos.**

## Accomplishments

- Mantiene OAuth, refresh tokens y autoridad de escritura dentro de Wyss. Home Edge sólo recibe
  eventos sanitizados y un cursor opaco; clientes y firmware nunca reciben credenciales.
- Separa acceso deshabilitado, lectura y escritura con scopes mínimos exactos. Un scope más amplio,
  incompleto o incoherente falla cerrado y la funcionalidad permanece apagada por defecto.
- Implementa full sync e incremental con hasta 20 páginas, instancias recurrentes, all-day,
  timezone de Córdoba, cancelaciones y recuperación atómica ante cursor HTTP 410.
- Conserva una cache SQLite privada y explícitamente stale ante proveedor caído, revinculación o
  revocación de write; revocar escritura no elimina la lectura ya sincronizada.
- Proyecta como máximo ocho próximos eventos, acota títulos e identifica IDs largos con SHA-256
  para mantener el mensaje del panel por debajo de 4 KiB sin reducir el cache autoritativo.
- Obliga crear, editar y eliminar a atravesar intención, plan B/C, policy, confirmación y
  reevaluación de Wyss; no existe un endpoint CRUD rápido en Home Edge.
- Renderiza próxima cita y cinco eventos en la card Agenda, incluidos all-day, tentativos,
  offline/cache y resumen de reposo, con regresión visual determinista.

## Commits

1. **Sincronización Calendar a través de Wyss** - `fe830a4`
2. **Agenda sanitizada en el panel** - `41c49f2`

## Remaining External Gates

O-07 debe registrar la aprobación del operador para los scopes exactos de lectura o escritura.
Después, una cuenta Google Calendar real debe demostrar consulta diaria/semanal y crear, editar y
eliminar desde PC, Android físico y panel pasando por confirmación. Sin esa cuenta y sin NVS v2
provisionada, CAL-01 y CAL-02 permanecen abiertos aunque la automatización esté completa.
