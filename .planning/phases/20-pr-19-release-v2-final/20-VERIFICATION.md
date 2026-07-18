---
phase: 20-pr-19-release-v2-final
status: release-prepared-publication-blocked
verified_at: 2026-07-18T02:00:00Z
requirements: [REL-01, REL-02, REL-03]
candidate_commit: generated-from-clean-head-after-this-document
---

# Verification: Phase 20

| Criterion | Evidence | Result |
| --- | --- | --- |
| 51 requisitos trazados y CI local | matriz JSON + verifier + suites completas | PASS AUTOMATED EVIDENCE / COMPLETION BLOCKED |
| Artefactos, checksums, SBOM, firma y docs | preparador + docs; clave real ausente | PASS PREP / SIGNATURE BLOCKED |
| Smoke físico completo mismo commit | hardware/cuentas/gates ausentes | BLOCKED PHYSICAL/EXTERNAL |
| O-06, recovery y downgrade | sin cambios irreversibles; ensayo real pendiente | BLOCKED OPERATOR/PHYSICAL |

## Controles del preparador

- Rechaza SemVer/commit/wheel/SBOM incompatibles, inputs vacíos y output no vacío.
- Copia contenido sin modificarlo y genera `SHA256SUMS` determinista.
- Produce `release-candidate.json` con board, commit, tamaño, hash y cinco gates.
- Produce `RELEASE_BLOCKED`; no firma, etiqueta, publica ni ejecuta Git/GitHub.

## Audit ejecutable de requisitos

`python tools/check_requirement_evidence.py --format json` informa 51/51 entradas: 45 `passed`,
2 `not_applicable` por ser evidencia física pura y 4 `blocked_external_gate` (CAM-01/02 y
REMOTE-01/02). Los 43 gates restantes se clasifican únicamente como 20 físicos, 12 externos y 11
de autorización. CI falla si desaparece un requisito/test/verificación, si un selector no existe o
si una fila abierta queda sin esa clasificación.

## Estado honesto

`REL-01` no puede completarse mientras existan requisitos físicos/externos pendientes y no haya CI
remoto protegido. `REL-02` carece de firma real, tag y publicación. `REL-03` carece de la matriz
física completa. El candidato local es evidencia de preparación, no una release final.
