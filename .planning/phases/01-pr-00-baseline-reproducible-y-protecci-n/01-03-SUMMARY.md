---
phase: 01-pr-00-baseline-reproducible-y-protecci-n
plan: "03"
subsystem: security
tags: [evidence, provenance, sha256, allowlist, fail-closed]
requires:
  - phase: 01-pr-00-baseline-reproducible-y-protecci-n
    provides: runner aislado del plan 01-01
provides:
  - Schema cerrado y manifest PR-00 en NOT_VERIFIED
  - Binding exacto por SHA y allowlist canónica repo-relative
  - Rechazo de simulaciones, secretos, rutas desplazadas y checksums inválidos
affects: [ci, physical-validation, release]
tech-stack:
  added: []
  patterns: [evidence provenance, exact-path allowlist, redacted validation]
key-files:
  created: [schemas/pr00-evidence.schema.json, tools/check_baseline_evidence.py, docs/evidence/pr-00/manifest.json]
  modified: [bridge/tests/test_baseline_runner.py]
key-decisions:
  - "La evidencia empieza sin SHA y NOT_VERIFIED; sólo branch protection puede ligarla al tested_commit."
patterns-established:
  - "Un item VERIFIED exige SHA exacto, UTC, provenance esperada, artifact_ref y sha256."
requirements-completed: [BASE-04]
duration: 5min
completed: 2026-07-17
---

# Phase 1 Plan 03: Evidencia fail-closed Summary

**Contrato cerrado que impide promover simulaciones o evidencia atribuida a otro commit.**

## Accomplishments

- Creó schema, allowlist, guía y manifest inicial sin anticipar el SHA probado.
- Implementó binding exacto y validación stdlib con salidas 0/1/40.
- Pasó 13 pruebas de evidencia y propagación del runner.

## Task Commits

1. **Contrato y manifest de evidencia** - `ef66c37`
2. **Validador y casos adversariales** - `ee4970f`

## Verification

- JSON de allowlist, schema y manifest válido.
- 13 pruebas enfocadas PASS; Ruff y formato PASS.
- Manifest canónico: 0/8 verificadas, exit 40, sin `tested_commit`.

## Next Phase Readiness

El tooling ya forma parte del HEAD que deberá medir CI antes del binding físico.

---
*Phase: 01-pr-00-baseline-reproducible-y-protecci-n*
*Completed: 2026-07-17*
