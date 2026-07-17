---
phase: 05-pr-04-shell-visual-wyss-core-y-modo-dormido
status: automated-passed-physical-pending
verified_at: 2026-07-17T21:34:53Z
requirements: [UI-01, UI-02, UI-03]
---

# Verification: Phase 5

| Requirement | Evidence | Result |
|---|---|---|
| UI-01 | Shell real LVGL con cinco destinos, conversación y reposo; nueve escenas renderizadas | PASS AUTOMATED |
| UI-02 | Tokens prueban ≥44 px, 33 ms activo y 125 ms dormido; faltan latencia/FPS/energía físicos y O-05 | PARTIAL |
| UI-03 | Simulador LVGL 8.4.0, textos largos, offline, confirmación, contraste y manifiesto visual | PASS |

## Commands

- `./scripts/verify_baseline.sh automated` → PASS.
- Python 3.14.6: 85 tests PASS; Ruff format/check y MyPy PASS.
- Arquitectura, doctor y documentación: PASS.
- CMake/CTest Release: 5/5 PASS, incluido `ui_visual_tests`.
- Simulador: nueve frames 800×480 coinciden con `tests/fixtures/ui_visual_manifest.txt`.
- Memoria LVGL simulada después de todos los escenarios: 50.760 bytes libres.
- PlatformIO ESP32-S3: SUCCESS; RAM 145.248/327.680 bytes (44,3 %), Flash
  1.581.081/6.553.600 bytes (24,1 %).

## Visual review

- Inicio online/offline: jerarquía y estado visibles, sin solapamientos.
- Hogar: encendido, brillo y tres escenas mantienen targets cómodos.
- Media/Agenda/Sistema: vacíos explícitos sin inventar datos.
- Conversación: mensaje largo envuelve y conserva Volver/Enviar.
- Confirmación: riesgo, pasos y dos decisiones permanecen visibles.
- Reposo: contexto y acceso manual no se solapan.

## Pending evidence

La fase no se declara cerrada. `UI-02` y el gate O-05 requieren la placa exacta, instrumentos y una
decisión del operador. El driver `SWITCH_EXPANDER` sólo soporta on/off, por lo que `18 %` es un token
lógico y no evidencia reducción de brillo o energía.

