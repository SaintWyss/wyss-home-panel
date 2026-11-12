---
phase: 11-pr-10-google-calendar
status: automated-and-panel-boot-passed-o07-account-pending
verified_at: 2026-07-18T00:41:05Z
requirements: [CAL-01, CAL-02]
---

# Verification: Phase 11

| Criterion | Evidence | Result |
|---|---|---|
| O-07 scopes separados mínimos | validación exacta automatizada; falta aprobación del operador | PENDING EXTERNAL |
| Agenda y CRUD real con confirmación | UI y flujo Wyss automatizados; falta cuenta y clientes reales | PENDING EXTERNAL + PHYSICAL |
| Sync/paginación/recurrencia/all-day/timezone/cursor | adapter, cache y pruebas de convergencia | PASS AUTOMATED |
| Revocar write conserva lectura sin tokens | restart sobre cache, proyección y rechazo de secretos | PASS AUTOMATED |

## Automated evidence

- Python completo: 152 tests PASS; única advertencia externa de deprecación TestClient.
- Ruff, Ruff format, MyPy estricto, arquitectura, doctor y documentación: PASS.
- CMake/CTest Release: 5/5 PASS, incluida regresión visual de 11 escenas.
- PlatformIO ESP32-S3: PASS; RAM 149.320 bytes (45,6 %), Flash 1.618.553 bytes (24,7 %).
- App SHA-256:
  `755cb32591c7f51db7b0f9c2d9efb4ef4ea16d43bd4d4263cf1f994f23ddf71d`.
- Snapshot Agenda `c0874d596dbe9e2f`; reposo con próximo evento `aaff744169de94cc`;
  LVGL terminó con 21.144 bytes libres.
- La proyección extrema de ocho eventos con IDs/títulos máximos queda bajo 4.096 bytes.

## Contract evidence

- La implementación sigue full sync inicial, `nextSyncToken`, paginación estable, cambios con
  eliminaciones e invalidación HTTP 410 documentados por Google.
- Scopes admitidos exactamente:
  `calendar.events.owned.readonly` para lectura y `calendar.events.owned` para escritura.
- Referencias oficiales:
  <https://developers.google.com/workspace/calendar/api/auth>,
  <https://developers.google.com/workspace/calendar/api/guides/sync>,
  <https://developers.google.com/workspace/calendar/api/v3/reference/events/list> y
  <https://developers.google.com/workspace/calendar/api/guides/recurringevents>.

## Physical panel evidence

- Commit exacto `41c49f2`; se escribió sólo la app en `0x10000`. NVS, bootloader, tabla de
  particiones, credenciales y eFuses no se tocaron.
- Serial confirmó `Wyss Home Panel 2.0.0`, placa Waveshare, display, LVGL y GT911
  (`TouchPad_ID:0x39,0x31,0x31`).
- La NVS v2 sigue ausente (`nvs_open failed: NOT_FOUND`), por lo que no se atribuye agenda real
  visible ni autenticación Calendar.
- Se restauró la app original de 5 MiB y el readback coincidió byte a byte con SHA-256
  `d7bbc1d350c3c24dcb5ccab0a75c3ae274b351463726cc0c13f2262b3a5f4be0`.
- El firmware original volvió a mostrar interfaz, conexión Wi-Fi y Tuya local operativo.

## Pending evidence

Aprobación O-07, OAuth real dentro de Wyss y smoke de consulta/crear/editar/eliminar desde PC,
Android físico y panel sobre el mismo commit. Esos gates mantienen CAL-01 y CAL-02 abiertos.
