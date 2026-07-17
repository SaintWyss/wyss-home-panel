# Phase 1: PR-00 — Baseline reproducible y protección - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-17
**Phase:** 01-pr-00-baseline-reproducible-y-proteccion
**Areas discussed:** ejecución reproducible, CI/protección de merges, evidencia física

---

## Ejecución reproducible

| Option | Description | Selected |
|--------|-------------|----------|
| Toolchains nativos fijados | Máxima transparencia, con mayor deriva del host | |
| Build containerizado | Oráculo hermético, peor acceso USB/serial | |
| Tooling híbrido aislado | Locks y caches locales conservando hardware nativo | ✓ |

**User's choice:** Selección automática recomendada por delegación del usuario.
**Notes:** Encaja con el baseline existente y permite diagnosticar cada capa.

---

## CI y protección de merges

| Option | Description | Selected |
|--------|-------------|----------|
| Workflow único bloqueante | Cinco jobs, acciones por SHA y un ruleset | ✓ |
| Workflows reutilizables | Más modularidad con mayor indirección | |
| Gates locales | Feedback rápido, pero no impide merges | |

**User's choice:** Selección automática recomendada por delegación del usuario.
**Notes:** Los required checks remotos son parte del criterio de cierre.

---

## Evidencia física

| Option | Description | Selected |
|--------|-------------|----------|
| Manifest fail-closed | Procedencia y estado verificables por máquina | ✓ |
| Notas best-effort | Contexto humano sin gate ejecutable | |
| Evidencia simulada | Útil para el harness, no para afirmar hardware real | |

**User's choice:** Selección automática recomendada por delegación del usuario.
**Notes:** La simulación nunca se promociona como evidencia física.

## Claude's Discretion

- Schema interno del manifest y composición exacta del runner.

## Deferred Ideas

- Ninguna.
