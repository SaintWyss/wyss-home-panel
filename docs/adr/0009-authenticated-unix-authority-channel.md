# ADR-0009 — Yo conecto Home Edge a Wyss mediante un socket Unix autenticado

**Estado:** aceptada.

## Contexto

Yo tenía un adapter HTTP v1 cuyos endpoints y payloads ya no coincidían con la autoridad Wyss. Ese canal exigía un token adicional y no separaba la capacidad Home de las operaciones owner.

## Decisión

Yo uso el socket Unix Home dedicado de Wyss como transporte productivo. El sistema operativo autentica al usuario Edge, Wyss valida `SO_PEERCRED` y limita el canal a `home.intent`, `home.plan.answer` y `status`. Yo conservo HTTP v1 sólo como rollback explícito mediante `transport = "http_v1"`.

## Consecuencias

Yo no abro puertos ni guardo otro token para conversar con Wyss. Yo acepto que el Edge y Wyss deban compartir un grupo de runtime y que las integraciones HTTP antiguas permanezcan desactivadas hasta tener métodos públicos equivalentes en la autoridad.
