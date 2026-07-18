---
phase: 10-pr-09-clima-semanal
status: automated-provider-and-panel-boot-passed-physical-projection-pending
verified_at: 2026-07-18T00:11:47Z
requirements: [WEATHER-01]
---

# Verification: Phase 10

| Criterion | Evidence | Result |
|---|---|---|
| Actual + siete dias, timezone y edad | tests, proveedor real y snapshots LVGL | PASS AUTOMATED + EXTERNAL |
| Offline, vencido, faltantes y proveedor caido | servicio, cache corrupta y snapshots explicitos | PASS AUTOMATED |
| Card manual/dormida y trafico | simulador, build y boot fisico; falta proyeccion real provisionada | PARTIAL PHYSICAL |

## Automated evidence

- Python completo: 137 tests PASS; unica advertencia externa de deprecacion TestClient.
- Ruff, Ruff format, MyPy estricto, arquitectura, doctor y documentacion: PASS.
- CMake/CTest Release: 5/5 PASS, incluida regresion visual de 11 escenas.
- PlatformIO ESP32-S3: PASS; RAM 147.488 bytes (45,0 %), Flash 1.615.965 bytes (24,7 %).
- Snapshot fresco `2ef49eb4fcfa9f64`, cache `c8c080a0cef0e4cb`, sin proveedor
  `d070fe3319432eb3` y dormido `2087736d7ad10516`.

## Real provider and traffic evidence

- Open-Meteo respondio HTTP 200 para `-27.4514,-58.9867`, timezone
  `America/Argentina/Cordoba`, current `2026-07-17T20:45`, 28,5 C y siete dias.
- Respuesta medida: 1.156 bytes en 1,173 s; SHA-256
  `b9c3ea9d2ba2c4ea2771d45d2f026bb44947342daf1ff961e1fe849f5cf4d0ff`.
- Con refresco cada 30 minutos: maximo 48 respuestas/dia, 55.488 bytes/dia de payload
  (54,2 KiB/dia), sin multiplicacion por los tres clientes gracias al lock/deduplicacion.
- Referencia del contrato: <https://open-meteo.com/en/docs>.

## Physical panel evidence

- Commit exacto `c332424`; app SHA-256
  `80986ae0f42058c334cd46e1b72c9a3c032153b5f587bf60544317029e769f1b`.
- Se escribio solo la app en `0x10000`; NVS, bootloader y tabla de particiones no se tocaron.
- Serial confirmo `Wyss Home Panel 2.0.0`, Waveshare ESP32-S3, display/LVGL y GT911
  (`TouchPad_ID:0x39,0x31,0x31`).
- La NVS v2 no estaba provisionada; por honestidad no se declara clima real visible en panel.
- Se restauro la app original y el readback de 5 MiB coincidio byte a byte con SHA-256
  `d7bbc1d350c3c24dcb5ccab0a75c3ae274b351463726cc0c13f2262b3a5f4be0`.
- El firmware original volvio a conectar Wi-Fi y Tuya local.

## Pending evidence

Provision v2 autorizado + Home Edge real con clima habilitado, seguido de observacion de la card
manual y dormida sobre el mismo commit. Esta pendiente fisica mantiene WEATHER-01 abierto.
