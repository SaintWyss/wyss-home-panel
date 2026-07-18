---
status: resolved
trigger: "Dejar el panel ESP32-S3 conectado a Wi-Fi e Internet usando los datos del proyecto viejo."
created: 2026-07-18T03:00:00Z
updated: 2026-07-18T03:36:00Z
---

# Debug: Wi-Fi/TLS stack canary

## Symptoms

- Expected: el panel obtiene red, establece WebSocket TLS con Home Edge y permanece estable.
- Actual: el display y el táctil arrancan; TLS recibe `errno 118 Host is unreachable` cada segundo.
- Error: tras cuatro o cinco reintentos, `wyss-network` dispara `Stack canary watchpoint` y reinicia.
- Timeline: apareció en la primera prueba física v2 después de migrar el NVS histórico.
- Reproduction: arrancar el firmware 2.0.0 ya configurado mientras Wi-Fi todavía negocia red.

## Current Focus

- hypothesis: confirmada.
- test: el inicio TLS quedó detrás de `WL_CONNECTED`; los mensajes de 4 KiB pasaron del stack al heap y el task de red aumentó a 16 KiB.
- expecting: cumplido; no hubo `Host is unreachable`, canario ni reboot durante 450 s de soak físico.
- next_action: cerrada.
- reasoning_checkpoint: el ELF confirmó 12.544 bytes de frames propios sobre un task de 12.288 bytes antes de sumar WebSocket/TLS.
- tdd_checkpoint: true

## Evidence

- timestamp: 2026-07-18T03:00:00Z
  observation: NVS válido, LCD/GT911 exitosos, bridge host saludable y accesible desde el host.
- timestamp: 2026-07-18T03:00:01Z
  observation: TLS empieza a los ~1.6 s sin esperar Wi-Fi y reinicia tras varios fallos.
- timestamp: 2026-07-18T03:20:00Z
  observation: el firmware corregido mantuvo TLS activo durante 450 s, con bridge activo y cero fallos seriales.
- timestamp: 2026-07-18T03:36:00Z
  observation: build PlatformIO, cinco pruebas C++/UI y 215 pruebas Python completaron correctamente.

## Eliminated

- hypothesis: el bridge local no arrancó
  reason: health TLS 2.0.0 responde y systemd reporta active/running sin reinicios.
- hypothesis: provisioning/NVS incompleto
  reason: el firmware dejó de reportar `nvs_open NOT_FOUND` y cargó la ruta configurada.

## Resolution

- root_cause: `WiFi.begin()` es asíncrono, pero el cliente TLS arrancaba inmediatamente; además tres frames propios de 4 KiB excedían por sí solos el stack de 12 KiB del task de red.
- fix: esperar `WL_CONNECTED`, reintentar el arranque de forma idempotente, mover los mensajes de 4 KiB al heap mediante colas de punteros, limpiar recursos parciales y ampliar el task a 16 KiB.
- verification: regresión estática dedicada, suite completa C++/UI, 215 pruebas Python, build ESP32, flash con hash verificado y soak físico de 450 s sin canarios ni reinicios.
- files_changed: `firmware/src/main.cpp`, `firmware/include/wyss/adapters/bridge_client.hpp`, `firmware/src/adapters/bridge_client.cpp`, `bridge/tests/test_firmware_network_safety.py`.
