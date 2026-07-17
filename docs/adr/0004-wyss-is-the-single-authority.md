# ADR-0004 — Yo mantengo a Wyss como autoridad única

**Estado:** aceptada para v2.0.0.

## Contexto

Yo ya tengo en `SaintWyss/Wyss` planificación, LLM, política A–D, pending, confirmación, executor, auditoría, web y Android. Si yo duplico esas decisiones en Home Edge o ESP32, creo bypasses y estados incompatibles.

## Decisión

Yo trato a Wyss como única autoridad. Yo permito un camino rápido doméstico sólo para acciones A reversibles, allowlisted y auditadas. Yo hago que el Edge y el panel proyecten estado, pero no clasifiquen riesgo global.

## Consecuencias

Yo obtengo un solo embudo y auditoría coherente. Yo acepto que capacidades personales queden bloqueadas cuando Wyss está caído, mientras preservo luces locales seguras.
