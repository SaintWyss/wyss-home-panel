---
phase: 13-pr-12-temporizadores
status: automated-and-firmware-build-passed-real-wyss-android-pending
verified_at: 2026-07-18T01:05:57Z
requirements: [TIMER-01, TIMER-02]
---

# Verification: Phase 13

| Criterion | Evidence | Result |
|---|---|---|
| Crear/pausar/reanudar/cancelar/presets multicliente | funnel Wyss y convergencia automatizados | PASS AUTOMATED + PENDING PHYSICAL |
| Reinicio y ajuste de reloj recuperan deadline | cache/restart y refresh monotónico | PASS AUTOMATED |
| 100 timers completan/notifican una vez | stress, dedupe y reinicio | PASS AUTOMATED + ANDROID PENDING |
| Exportar/reimportar activos preserva estado | round-trip SQLite privado | PASS AUTOMATED |

## Automated evidence

- Python completo: 178 tests PASS; única advertencia externa de deprecación TestClient.
- Ruff, Ruff format y MyPy estricto: PASS.
- CMake/CTest Debug: 5/5 PASS, incluida regresión visual de 11 escenas.
- Stress: 100 `timer.completed`, 100 `notification.delivered`; segunda corrida y reinicio producen
  cero duplicados.
- PlatformIO ESP32-S3: PASS; RAM 150.072 bytes (45,8 %), Flash 1.623.209 bytes (24,8 %).
- App SHA-256:
  `353906395b581e420f6aa2d7f7491c9432aae95a77ebfc24beb5cacf4ddd4607`.
- Agenda con timer `e53d5080e4c0f8fb`; reposo `057b8d91b8c0b5ad`; LVGL terminó con 20.824
  bytes libres.

## Safety and physical state

- `timers_enabled` está apagado por defecto. Sin Wyss, Home Edge no inventa timers ni deadlines.
- La pantalla física no fue reflasheada: sigue con firmware original, Wi-Fi y Tuya funcionales.
  NVS, credenciales, bootloader, particiones y eFuses no fueron modificados.
- La notificación Android sigue detrás de O-04 y del adapter inyectable de fase 12.

## Pending evidence

Scheduler Wyss real, creación/pausa/reanudación/cancelación/preset desde PC/Android/panel y
notificación única en Android físico sobre el mismo commit.
