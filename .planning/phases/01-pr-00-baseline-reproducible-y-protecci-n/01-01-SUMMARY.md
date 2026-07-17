---
phase: 01-pr-00-baseline-reproducible-y-protecci-n
plan: "01"
subsystem: testing
tags: [uv, platformio, cmake, baseline, reproducibility]
requires: []
provides:
  - Runner aislado para bridge, dominio C++, firmware, doctor y documentación
  - Códigos estables 10/20/30/40 para código, dependencias, entorno y evidencia
affects: [ci, evidence, release]
tech-stack:
  added: []
  patterns: [toolchains aislados bajo .cache/wyss-baseline, gates fail-closed]
key-files:
  created: [scripts/verify_baseline.sh, bridge/tests/test_baseline_runner.py]
  modified: [config/baseline-versions.toml, README.md, .gitignore]
key-decisions:
  - "Python 3.14.6 y CMake 4.1.2 quedan registrados como versiones exactas del baseline."
patterns-established:
  - "El modo automated sólo valida lo automatizable; all exige evidencia VERIFIED."
requirements-completed: [BASE-01, BASE-02, BASE-03]
duration: 12min
completed: 2026-07-17
---

# Phase 1 Plan 01: Runner reproducible Summary

**Un único runner aislado reproduce bridge, C++, firmware y gates operativos sin usar caches globales.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-07-17T17:08:37-03:00
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Registró versiones exactas y aisló uv, PlatformIO y CMake bajo el repositorio.
- Validó 21 pruebas Python, 2 pruebas C++ y el firmware ESP32-S3 completo.
- Probó códigos 10/20/30/40 y redacción de variables sensibles.

## Task Commits

1. **Runner aislado y versiones exactas** - `e3270ba`
2. **Contratos del runner y documentación** - `5044ddb`

## Verification

- `./scripts/verify_baseline.sh automated` → PASS.
- Firmware: RAM 96.048 bytes (29,3 %), Flash 1.574.853 bytes (24,0 %).
- `./scripts/verify_baseline.sh all` → exit 40 por evidencia aún ausente, como exige el contrato.
- Runtime v1 y provisioning permanecen sin cambios respecto de `53203cd`.

## Deviations from Plan

Se añadió `.cache/` a `.gitignore` para impedir que los toolchains locales entren en Git.

## Next Phase Readiness

El runner está listo para integrar el validador fail-closed de evidencia del plan 01-03.

---
*Phase: 01-pr-00-baseline-reproducible-y-protecci-n*
*Completed: 2026-07-17*
