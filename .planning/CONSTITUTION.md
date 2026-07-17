# Wyss Home Panel — Constitution

**Version:** 1.0 — 2026-07-17

## P1 — Autoridad única de Wyss (MUST)

Toda intención, plan, confirmación, ejecución y auditoría doméstica debe atravesar la política A–D y el funnel público de Wyss. Rationale: un camino alternativo desde UI, móvil o adapter permitiría eludir la política y producir autoridades contradictorias.

## P2 — Arquitectura hexagonal (MUST)

Cada capacidad debe definir contrato y port antes del adapter; dominio y aplicación deben permanecer independientes de frameworks e infraestructura. Rationale: los límites sustituibles permiten contract tests, rollback y evolución sin reescrituras laterales.

## P3 — Compatibilidad y reversibilidad (MUST)

Cada incremento v2 debe conservar v1 hasta completar su migración y debe declarar un rollback comprobable que no destruya datos ni credenciales. Rationale: el panel doméstico existente debe seguir operable durante toda la entrega.

## P4 — Fronteras cerradas y fail-closed (MUST)

Toda entrada de red o proveedor debe autenticarse, validarse contra schemas cerrados, limitarse por capacidad y fallar de forma cerrada con idempotencia y rate limit donde corresponda. Rationale: cada nueva frontera amplía la superficie de una red doméstica y no puede confiar en el cliente.

## P5 — Secretos fuera de clientes y logs (MUST NOT)

El firmware, las proyecciones, los fixtures, los repositorios y los logs no deben contener credenciales domésticas, tokens OAuth, claves privadas ni material de revocación. Rationale: el Home Edge es la frontera mínima autorizada para esos secretos y los clientes físicos pueden perderse o extraerse.

## P6 — Una autoridad mutable por dato (MUST)

Cada dato mutable debe declarar una única autoridad; los demás componentes sólo pueden mantener proyecciones revisionadas o caches acotados y reconciliables. Rationale: la convergencia multicliente exige impedir estados maestros paralelos.

## P7 — Evidencia antes de completar (MUST)

Cada fase debe incluir tests automatizados, checks estáticos, evidencia de rollback y, cuando el criterio dependa de hardware o servicio real, evidencia física vinculada al commit exacto o un bloqueo explícito. Rationale: una simulación o un documento no prueban el comportamiento del sistema doméstico real.

## P8 — Sin cambios irreversibles implícitos (MUST NOT)

Ningún plan debe quemar eFuses ni cambiar credenciales, cuentas, autenticación, particiones, bootloader o datos persistentes sin autorización explícita del operador. Rationale: esos cambios exceden un incremento reversible y pueden dejar el dispositivo o los datos irrecuperables.

---

## Amendment Log

| Version | Date | Change | Reason |
|---------|------|--------|--------|
| 1.0 | 2026-07-17 | Initial constitution | Project inception |
