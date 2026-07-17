---
phase: 06-pr-05-luces-completas-y-migracion-del-baseline
subsystem: home-lights
tags: [tuya, home-assistant, light-port, websocket, idempotency, lvgl]
requires:
  - phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
    provides: event log y proyecciones revisionadas
  - phase: 05-pr-04-shell-visual-wyss-core-y-modo-dormido
    provides: shell LVGL y regresión visual
provides:
  - LightPort único para Tuya LAN multientidad y Home Assistant
  - Comandos verificados de encendido, brillo, color y escenas
  - Serialización por entidad, idempotencia durable y audit trail privado
  - Convergencia WebSocket en vivo para PC, Android y panel
  - Vista Hogar multiluces con disponibilidad y rollback optimista
requirements-partial: [LIGHT-01, LIGHT-02, LIGHT-03]
completed-automated: 2026-07-17
---

# Phase 6: Complete lights and baseline migration Summary

**La implementación automatizable está completa; el cierre exige LEDVANCE, red y clientes físicos.**

## Accomplishments

- Migró Tuya LAN detrás de un `LightPort` multientidad sin romper el protocolo v1.
- Agregó DPS configurables, color HSV/RGB, escenas declarativas y estados indisponibles sin borrar
  el último valor verificado.
- Implementó el mismo contrato mediante Home Assistant como adapter opcional.
- Resolvió secretos anidados por variable de entorno para cada foco sin materializarlos en Git.
- Serializó órdenes por entidad y mantuvo paralelismo entre luces independientes.
- Agregó un journal SQLite privado que distingue `accepted`, `verified`, `failed` y `ambiguous`;
  nunca repite un `toggle` de resultado incierto.
- Publicó el estado completo de hogar a PC, Android y panel mediante WebSocket, sin polling y con
  capacidades independientes por tipo de cliente.
- Conservó el camino v1 sobre el mismo servicio cuando la migración está activa.
- Probó 500 cambios verificados, fallos de proveedor, replay, concurrencia, estado offline y
  rollback del feature flag sin borrar identidades, eventos, proyecciones o auditoría.
- Rediseñó Hogar para tres luces visibles, disponibilidad textual, selección, brillo, cuatro
  presets de color y escenas dinámicas; los controles indisponibles quedan deshabilitados.

## Commits

1. **Adapters multiluces y compatibilidad v1** - `9ceef91`
2. **Servicio serializado y journal durable** - `1ecbce5`
3. **Convergencia v2 en vivo para tres clientes** - `88e0189`
4. **Controles multiluces en el panel** - `5a9e287`
5. **Gate reversible de migración de luces** - `5905062`

## Rollback

- `protocol_v2.lights_enabled = false` rechaza nuevas órdenes v2 y mantiene el listener/proyección.
- `/v1/panel` vuelve al gateway compatible sin tocar credenciales, NVS ni firmware.
- `identity_db`, `event_db`, `projection_db` y `light_audit_db` no se eliminan ni migran al volver.
- El binario estable y la carga USB continúan como camino físico; no se escribió eFuse ni NVS.

## Physical Setup Pending

- Ejecutar encendido, brillo, color y escena sobre la LEDVANCE/Tuya LAN 3.3 real.
- Medir comando→estado verificado en LAN saludable y demostrar ≤150 ms p95.
- Repetir los 500 cambios con la luz, Wi-Fi y placa exactas.
- Probar caída/recuperación de Wi-Fi, clave inválida y foco offline reales.
- Ejecutar desde PC, Android y panel físicos sobre el mismo commit.
- Volver al adapter/binario estable en el equipo real y confirmar credenciales/NVS intactos.
