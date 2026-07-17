---
phase: 08-pr-07-push-to-talk-pc-y-android
status: automated-passed-external-physical-pending
verified_at: 2026-07-17T23:11:27Z
requirements: [VOICE-01, VOICE-02]
---

# Verification: Phase 8

| Requirement | Evidence | Result |
|---|---|---|
| VOICE-01 | PTT, edición, cancelación y segundo gesto explícito; intent usa funnel compartido | PASS AUTOMATED / O-01 + PHYSICAL PENDING |
| VOICE-02 | silencio, ruido, timeout, proveedor caído, capability, flag y borrado probados | PASS AUTOMATED / PHYSICAL AUDIO MATRIX PENDING |

## Automated evidence

- Python: 116 tests PASS; incluye ciclo de voz y endpoints autenticados.
- Ruff check/format, MyPy estricto y límites arquitectónicos: PASS.
- CMake/CTest Release: 5/5 PASS.
- PlatformIO ESP32-S3: PASS; voz no incrementa RAM/Flash del panel porque corre en PC/Android.
- Node syntax check del cliente: PASS.

## Browser QA

- Render headless verificado en 375×812, 768×1024 y 1280×900.
- Sin overflow horizontal ni errores de consola.
- Todos los labels apuntan a controles, el live region usa `role=status` y la altura táctil mínima
  observada es 44 px.
- Con voz desactivada, el PTT queda deshabilitado y escribir texto habilita “Enviar a Wyss”.

## Privacy and failure matrix

| Caso | Resultado automatizado |
|---|---|
| Transcripción exitosa | devuelve sólo texto editable; no crea evento ni llama a Wyss |
| Silencio o ruido | 422 recuperable; no envío implícito |
| Provider caído o timeout | 503/504 recuperable; texto sigue disponible |
| Capacidad ausente | 403 antes de entregar audio al provider |
| Voice flag apagado | PTT rechazado; `input=text` sigue aceptado |
| Buffer crudo | sobrescrito en éxito y error; no entra a proyección/event log |
| Interrupción de UI | tracks detenidos y transcripción cancelada; intent explícito no se aborta |

## Pending evidence

O-01 impide declarar un STT real por defecto: el adapter productivo falla cerrado hasta que el
operador elija el motor mediante benchmark. Luego deben ejecutarse la matriz física en PC y Android,
la precisión con español argentino y la inspección de permisos/retención del proveedor elegido.
