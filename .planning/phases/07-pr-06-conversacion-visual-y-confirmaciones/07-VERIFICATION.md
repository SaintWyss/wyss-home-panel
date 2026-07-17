---
phase: 07-pr-06-conversacion-visual-y-confirmaciones
status: automated-passed-physical-pending
verified_at: 2026-07-17T22:48:43Z
requirements: [CONV-01, CONV-02]
---

# Verification: Phase 7

| Requirement | Evidence | Result |
|---|---|---|
| CONV-01 | Tres WebSockets reciben la misma secuencia completa; firmware v2 consume snapshot+deltas y compila | PASS AUTOMATED / PHYSICAL E2E PENDING |
| CONV-02 | A/B/C/D, TTL, CAS, `CONFIRMAR`, carrera, rechazo, D y reevaluación fail-closed probados | PASS AUTOMATED |

## Automated evidence

- Python: 108 tests PASS; incluye servicio conversacional y PC/Android/panel simultáneos.
- Ruff check/format, MyPy estricto y límites arquitectónicos: PASS.
- Contrato compartido Python/C++: intents y respuestas válidas/maliciosas cubiertos.
- CMake/CTest Release: 5/5 PASS, incluida regresión visual LVGL.
- PlatformIO ESP32-S3: PASS; 145.992 bytes de RAM (44,6 %) y 1.599.445 bytes de Flash
  (24,4 %).

## Physical hardware evidence

- Panel real detectado como ESP32-S3 Waveshare por `/dev/ttyACM0`.
- Se leyó antes de la prueba la partición factory activa de 5 MiB para disponer de un rollback
  byte a byte, sin leer ni escribir NVS.
- La app v2 se grabó temporalmente sólo en la partición de aplicación `0x10000`; esptool verificó
  el hash escrito.
- Arranque físico PASS: placa Waveshare inicializada, controlador táctil GT911 detectado y LVGL
  iniciado. La prueba no provisionó credenciales v2 ni alteró bootloader o tabla de particiones.
- Se restauró la partición de aplicación original leída de la propia placa. El reinicio posterior
  confirmó interfaz lista, Wi-Fi conectado y `TUYA_LOCAL_OK`.

## Policy matrix

| Caso | Resultado automatizado |
|---|---|
| A sin pending | `thinking → response → verified` |
| B aprobado | exige revisión 1, `CONFIRMAR` y reevaluación |
| B rechazado | reevalúa, resuelve y vuelve a `idle` |
| C sin palabra o vencido | no llama a ejecución de Wyss |
| D | `policy_rejected`; no existe bypass confirmable |
| Dos confirmaciones simultáneas | una resuelve; la otra recibe `already_resolved` |
| Revisión obsoleta | `conflict` fail-closed |
| Reevaluación no acreditada | no publica `plan.resolved` ni ejecuta |
| Streaming desactivado | respuesta completa y misma política |
| Capacidad ausente | rechazo antes de contactar Wyss |

## Pending evidence

El panel real ya demuestra arranque, display, touch y rollback de la app. El fake de Wyss demuestra
el contrato y todas las ramas de política, pero no sustituye el daemon, red ni identidades reales.
CONV-01 permanece parcial hasta provisionar una identidad v2 autorizada y recorrer el ciclo completo
en PC, Android y panel reales sobre el mismo commit.
