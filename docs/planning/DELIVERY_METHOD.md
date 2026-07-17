# Método de entrega

## Principio

Yo preservo el sistema que funciona y hago cambios incrementales con evidencia. Yo no reescribo por moda, no mezclo refactor con feature sin necesidad y no declaro éxito sin probar el camino observable.

## Ciclo por capacidad

1. Yo leo el estado real y documento la brecha.
2. Yo actualizo decisión, requisito y criterio de aceptación.
3. Yo cambio el port/contrato antes del adapter.
4. Yo escribo test de dominio/contrato que falla por la brecha.
5. Yo implemento dominio y aplicación sin frameworks.
6. Yo implemento adapter y composition root.
7. Yo pruebo errores, seguridad, degradación y rollback.
8. Yo mido rendimiento si toca un camino crítico.
9. Yo actualizo UML, operación y trazabilidad.
10. Yo publico un PR de alcance cerrado con evidencia.

## Reglas SOLID y hexagonales

- Yo doy una sola razón de cambio a cada módulo.
- Yo extiendo mediante adapters, no condicionales repartidos.
- Yo mantengo sustitución mediante contract tests.
- Yo creo ports pequeños por capacidad.
- Yo invierto dependencias hacia dominio y application.
- Yo prohíbo imports laterales entre adapters.
- Yo mantengo bootstrap como cableado, no lógica.

## Seguridad integrada

Yo hago threat modeling antes de abrir una frontera. Yo uso fail-closed, least privilege, schemas cerrados, allowlists, idempotencia y auditoría. Yo no creo un path especial para UI, móvil, rutinas o integraciones. Yo reevalúo política al confirmar y valido de nuevo en la segunda muralla.

## Pull requests

Yo uso `agent/<alcance>` y commits semánticos. Yo mantengo PR pequeño, diff intencional y descripción en primera persona con qué, por qué, impacto, checks y rollback. Yo no fusiono con CI rojo, deuda secreta o archivos no relacionados.

## Evidencia

Yo registro comando, resultado, commit, hardware, versión y fecha. Yo diferencio test automatizado, simulación y smoke físico. Yo no convierto una observación manual en una garantía general sin muestra.

## Decisiones

Yo creo ADR cuando cambia autoridad, frontera, persistencia, seguridad, protocolo o dependencia difícil de revertir. Yo no creo ADR por detalles locales triviales. Yo marco superseded en vez de borrar historia.

## Gestión de riesgo

Yo mantengo un registro con severidad, probabilidad, mitigación, owner y gate. Yo bloqueo release por riesgo crítico/alto sin resolver. Yo documento límites conocidos menores con impacto y workaround.

## Definición de terminado

Yo exijo código, tests, tipos/static checks, seguridad, docs, observabilidad, migración, compatibilidad, performance, accesibilidad, rollback y evidencia según alcance. Yo no acepto TODO sin issue/decisión ni feature flag sin fecha de retiro.
