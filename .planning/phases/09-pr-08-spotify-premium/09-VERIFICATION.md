---
phase: 09-pr-08-spotify-premium
status: automated-and-panel-boot-passed-external-account-pending
verified_at: 2026-07-17T23:39:13Z
requirements: [MEDIA-01, MEDIA-02]
---

# Verification: Phase 9

| Requirement | Evidence | Result |
|---|---|---|
| MEDIA-01 | contrato, scopes, comandos, proyección triple y UI panel | PASS AUTOMATED / O-07 + PREMIUM REAL PENDING |
| MEDIA-02 | 204/401/403/404/429, malformed, replay, flag y no-token | PASS AUTOMATED / OAUTH REAL PENDING |

## Automated evidence

- Python focal: 27 tests PASS para adapter, servicio, config y WebSocket multicliente.
- Python baseline completo: 129 tests PASS; única advertencia externa de deprecación TestClient.
- Ruff, MyPy estricto, límites arquitectónicos y fixtures Python/C++ compartidos: PASS.
- CMake/CTest Release: 5/5 PASS, incluido snapshot visual MEDIA.
- PlatformIO ESP32-S3: PASS; RAM 146.664 bytes (44,8 %), Flash 1.612.493 bytes (24,6 %).
- Snapshot MEDIA: `fcfc1b7ddc820165`; controles de 48–58 px y estado textual además de color.

## Failure and privacy matrix

| Caso | Resultado automatizado |
|---|---|
| 204 sin playback | estado vinculado pero no disponible, recuperable |
| 401 | `reauthorization_required` sin cuerpo remoto ni token |
| 403 | error explícito de Premium/scope |
| 404/dispositivo inactivo | error explícito; panel deshabilita controles |
| 429 | conserva pista/dispositivo, publica degradación y `retry_after` acotado |
| respuesta inválida/red caída | `provider_unavailable` fail-closed |
| replay/revisión obsoleta | una ejecución o `conflict`, sin doble comando |
| flag apagado | Spotify oculto/rechazado; health, v1, luces y shell continúan |
| credenciales | no existen en dominio, proyección, firmware, fixtures de playback o errores |

## Physical panel evidence

- Commit exacto: `6efca4b`; app binaria SHA-256
  `7cf29f5eb89b845fbf846839ea2e7d20c9c4a239ebe9844422d0dae2dbd1997e`.
- Se escribió sólo la app en `0x10000`; NVS, bootloader y tabla de particiones no se tocaron.
- Serial confirmó `Wyss Home Panel 2.0.0`, Waveshare ESP32-S3, display/LVGL y GT911
  (`TouchPad_ID:0x39,0x31,0x31`).
- Se restauró la app original y el readback de 5 MiB coincidió byte a byte con SHA-256
  `d7bbc1d350c3c24dcb5ccab0a75c3ae274b351463726cc0c13f2262b3a5f4be0`.
- El firmware original volvió a conectar Wi-Fi y Tuya local.

## Pending evidence

O-07 no fue aprobado y no hay cuenta Premium autorizada. Por eso `spotify_enabled` permanece
apagado y esta fase no declara OAuth, refresh ni control real del proveedor como evidencia física.
