# ADR-0005 — Yo organizo por dominio y no por integración

**Estado:** aceptada para v2.0.0.

## Contexto

Yo necesito luces, Spotify, clima, Calendar, recordatorios, temporizadores, cámaras y voz. Un repositorio por función multiplicaría CI, secretos, releases, despliegues y contratos sin independencia real.

## Decisión

Yo mantengo integraciones personales dentro de `SaintWyss/Wyss` y capacidades físicas dentro de `wyss-home-panel`. Yo separo mediante ports/adapters y bounded contexts. Yo extraigo un repositorio sólo si obtiene despliegue, ciclo de vida y consumidores independientes.

## Consecuencias

Yo reduzco operación y conservo aislamiento lógico. Yo debo hacer cumplir límites mediante import rules y tests para evitar un monolito acoplado.
