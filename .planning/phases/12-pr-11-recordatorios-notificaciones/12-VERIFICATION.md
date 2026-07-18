---
phase: 12-pr-11-recordatorios-notificaciones
status: automated-and-firmware-build-passed-o04-android-pending
verified_at: 2026-07-18T00:54:32Z
requirements: [REM-01, REM-02]
---

# Verification: Phase 12

| Criterion | Evidence | Result |
|---|---|---|
| O-04 mecanismo Android | adapter reemplazable y apagado por defecto; falta decisión física | PENDING EXTERNAL |
| Reminder durable, recurrente, completable y posponible | cache/restart/proyección y funnel Wyss automatizados | PASS AUTOMATED |
| Notificación única recuperable con deep link | outbox/retry/dedupe automatizados; falta teléfono real | PASS AUTOMATED + PENDING PHYSICAL |
| Desactivar push no pierde el reminder | cache y outbox persisten con entrega apagada | PASS AUTOMATED |

## Automated evidence

- Python completo: 164 tests PASS; única advertencia externa de deprecación TestClient.
- Ruff, Ruff format y MyPy estricto: PASS.
- CMake/CTest Debug: 5/5 PASS, incluida regresión visual de 11 escenas.
- PlatformIO ESP32-S3: PASS; RAM 149.808 bytes (45,7 %), Flash 1.621.593 bytes (24,7 %).
- App SHA-256:
  `d64d5f444605f68054cb4fdd3845a369d8925023a71bf363b870600bb90f5894`.
- Agenda con reminders `09b532cc2bc20d5e`; reposo `dd16e0f9c9ac388f`; LVGL terminó con
  20.832 bytes libres.
- Tres clientes reciben igual proyección con una consulta; permisos negados conservan cache y
  reintentan; reinicio posterior a ack no vuelve a entregar.

## Safety and physical state

- `reminders_enabled` y `notifications_enabled` están apagados por defecto. Configuración rechaza
  notificaciones sin recordatorios.
- No se eligió Capacitor, FCM ni otro canal y no se tocó una cuenta Android: O-04 lo impide.
- La pantalla física no fue reflasheada en esta fase. Continúa ejecutando el firmware original
  restaurado y verificado con Wi-Fi/Tuya local; NVS, credenciales, bootloader, particiones y eFuses
  no fueron modificados.

## Pending evidence

ADR O-04, teléfono Android físico, permisos permitidos/negados, background, deep link real y smoke
contra recordatorios autoritativos del Wyss real sobre el mismo commit.
