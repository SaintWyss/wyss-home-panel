# ADR-0007 — Yo sincronizo mediante snapshot y eventos

**Estado:** aceptada para v2.0.0.

## Contexto

Yo quiero controlar desde PC, Android y panel sin estados divergentes ni polling agresivo.

## Decisión

Yo uso snapshot inicial, eventos delta, revisión por agregado, cursor de reanudación e idempotencia. Yo trato la entrega como al menos una vez y hago consumidores idempotentes.

## Consecuencias

Yo obtengo menor latencia y tráfico. Yo asumo complejidad explícita de reconexión, conflictos y compatibilidad, protegida por contract tests.
