---
phase: 06-pr-05-luces-completas-y-migracion-del-baseline
status: automated-passed-physical-pending
verified_at: 2026-07-17T22:14:23Z
requirements: [LIGHT-01, LIGHT-02, LIGHT-03]
---

# Verification: Phase 6

| Requirement | Evidence | Result |
|---|---|---|
| LIGHT-01 | Tuya/HA implementan un `LightPort`; PC, Android y panel reciben el mismo delta; UI cubre varias luces, color, escenas y disponibilidad | PASS AUTOMATED / PHYSICAL PENDING |
| LIGHT-02 | Firmware pinta optimista y revierte a 2,5 s; Edge publica sólo estado verificado | PASS AUTOMATED / p95 PHYSICAL PENDING |
| LIGHT-03 | 500 cambios, serialización, fallo offline, replay, journal y rollback del flag probados | PASS AUTOMATED / PHYSICAL FAULT MATRIX PENDING |

## Automated evidence

- Python: 99 tests PASS; incluye tres WebSockets simultáneos y 500 comandos persistidos.
- Ruff check/format, MyPy estricto y límites arquitectónicos: PASS.
- CMake/CTest Release: 5/5 PASS con fixtures v2 compartidos Python/C++.
- Regresión visual: diez escenas 800×480; incluye Hogar multiluces y luz indisponible.
- Memoria LVGL simulada al finalizar: 33.928 bytes libres.
- PlatformIO ESP32-S3: PASS; 145.936 bytes de RAM (44,5 %) y 1.588.893 bytes de Flash
  (24,2 %).
- Baseline integral `./scripts/verify_baseline.sh automated`: PASS.

## Failure and rollback matrix

| Caso | Evidencia automatizada | Resultado |
|---|---|---|
| Misma entidad concurrente | lock por entidad; máximo observado 1 | PASS |
| Luces distintas | progresan sin lock global de hardware | PASS |
| Replay exacto | devuelve el evento original sin segunda ejecución | PASS |
| Key reutilizada con otro payload | conflicto fail-closed | PASS |
| Toggle interrumpido | queda `ambiguous` y no se repite | PASS |
| Proveedor/foco offline | error explícito y último estado verificado conservado | PASS |
| Cliente WebSocket caído | se aísla sin fallar el comando de luz | PASS |
| `lights_enabled = false` | v2 queda read-only, v1 sigue y las cuatro bases permanecen | PASS |

## Pending evidence

La fase no se declara cerrada. El adapter fake prueba contratos, carreras y degradación, pero no
demuestra tiempos ni comportamiento eléctrico/red de la LEDVANCE real. LIGHT-01/02/03 conservan
pendiente físico hasta ejecutar la matriz sobre panel, foco, Android y PC reales ligados al mismo
commit.
