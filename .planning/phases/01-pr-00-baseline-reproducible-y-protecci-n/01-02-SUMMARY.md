---
phase: 01-pr-00-baseline-reproducible-y-protecci-n
plan: "02"
subsystem: ci-security
tags: [github-actions, branch-protection, required-checks, evidence]
requires:
  - phase: 01-pr-00-baseline-reproducible-y-protecci-n
    provides: contrato CI y evidencia fail-closed commiteados
provides:
  - Cinco contextos CI observados sobre el commit exacto
  - Protección remota de main validada por GET
  - Evidencia redactada de la configuración aplicada
affects: [ci, release, physical-validation]
key-files:
  created: [docs/evidence/pr-00/branch-protection.json]
  modified: [tools/check_ci_protection.py, bridge/tests/test_ci_protection.py, bridge/tests/test_baseline_evidence.py]
key-decisions:
  - "Los check-runs duplicados por push y PR son seguros sólo si todas las ocurrencias terminan en success sobre el mismo SHA."
requirements-completed: [BASE-05]
completed: 2026-07-18
---

# Phase 1 Plan 02: CI remota y protección de main

**`main` quedó protegido por los cinco checks bloqueantes sobre el commit probado.**

## Accomplishments

- El operador emitió la señal literal `APROBAR PUBLICACIÓN Y PROTECCIÓN`.
- Publicó `fd8a01d9e44d989017b4006eee432e4dc9b6bc53` mediante push normal y observó
  dos workflows completos, con las diez ocurrencias de los cinco contextos en `success`.
- Corrigió el validador para tratar de forma fail-closed los contextos repetidos que GitHub crea
  cuando el mismo SHA recibe eventos `push` y `pull_request`.
- Hizo que el fixture de evidencia cree una plantilla neutral y no dependa del estado ya ligado del
  manifest canónico.
- Confirmó por GET `strict=true`, cinco checks exactos, administradores incluidos, una aprobación,
  conversaciones resueltas y force-push/borrado deshabilitados.

## Commits

1. **Contrato CI y protección** - `381c110`
2. **Validación segura de contextos repetidos** - `fd8a01d`

## Verification

- `python tools/check_ci_protection.py --local`: PASS.
- 18 pruebas enfocadas de CI/calidad: PASS.
- Workflows `29626641230` y `29626642885`: PASS en los cinco jobs.
- GET remoto validado por `tools/check_ci_protection.py --remote-json`: VERIFIED.

## Next Phase Readiness

BASE-05 está cerrado. El manifest físico puede ligarse al tested commit; BASE-04 continúa abierto
hasta reunir backup, métricas y smoke reales sin sustituirlos por simulación.

---
*Phase: 01-pr-00-baseline-reproducible-y-protecci-n*
*Completed: 2026-07-18*
