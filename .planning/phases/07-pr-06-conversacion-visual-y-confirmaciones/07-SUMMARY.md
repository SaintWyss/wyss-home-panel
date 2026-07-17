---
phase: 07-pr-06-conversacion-visual-y-confirmaciones
subsystem: conversation
tags: [wyss, websocket, confirmation, ttl, cas, lvgl]
requires:
  - phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
    provides: event log, snapshot y deltas multicliente
provides:
  - Sesión conversacional única para PC, Android y panel
  - Funnel A-D con TTL, CAS, primera respuesta válida y reevaluación en Wyss
  - Streaming reversible a respuesta completa sin cambiar política
  - Cliente firmware v2 de producción con rollback compilable a v1
requirements-complete: [CONV-02]
requirements-partial: [CONV-01]
completed-automated: 2026-07-17
---

# Phase 7: Conversation and confirmations Summary

**La implementación y el arranque físico están verificados; el cierre E2E exige Wyss y tres clientes reales.**

## Accomplishments

- Enrutó `assistant.intent` y `plan.answer` por un único servicio sin duplicar planificación,
  clasificación ni ejecución de Wyss.
- Serializó la sesión compartida y bloqueó una segunda intención mientras existe un pending válido.
- Proyectó `idle`, `thinking`, `awaiting_confirmation`, `executing`, `verified` y `failed` en vivo.
- Hizo idempotente el `request_id` y rechazó su reutilización con otro texto.
- Aplicó TTL monotónico acotado, revisión CAS, `CONFIRMAR` exacto y primera respuesta válida.
- Exigió `policy_reevaluated = true` de Wyss antes de resolver; B/C fallan cerradas y D nunca crea
  un pending confirmable.
- Probó A, B, C y D, aprobación, rechazo, vencimiento, carrera, replay, falta de capacidad y falla
  de reevaluación.
- Conservó respuesta completa con `conversation_streaming = false` y el mismo circuito de política.
- Migró el firmware productivo a `/v2/client`, snapshot+deltas y cursor en RAM; PC, Android y panel
  reciben los mismos eventos.
- Conservó `/v1/panel` y `WYSS_PROTOCOL_V2_CLIENT=0` como rollback sin escribir NVS.

## Commits

1. **Funnel conversacional compartido y contratos** - `18f2d64`
2. **Cliente v2 productivo en el panel** - `352b9ff`
3. **Estado idle después del rechazo** - `4dfafa6`

## Physical Setup Pending

- El panel real ya pasó arranque v2, inicialización de display/touch y rollback exacto a la app
  original con Wi-Fi y Tuya recuperados.
- Ejecutar A, B, C y D contra el daemon Wyss real del owner.
- Enviar texto y confirmar desde PC, Android y panel físicos sobre el mismo commit.
- Cortar y recuperar WSS durante `thinking`, pending y ejecución.
- Validar visualmente texto largo, modal táctil, expiración y resolución desde otro cliente.
- Provisionar de forma autorizada la identidad v2; la prueba temporal no escribió NVS.
