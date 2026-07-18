# Soak v2.0.0

## Evidencia automatizada reproducible

Yo ejecuto desde la raíz:

```bash
uv run --project bridge --locked wyss-soak
```

El comando usa los stores SQLite, `LightService`, `TimerService` y
`ProjectionCoordinator` reales. En un directorio temporal limpio ejecuta:

- 500 cambios de brillo revisionados y verifica el estado final;
- replay de una orden verificada después de recrear el proceso;
- una caída cerrada del provider de luces y una recuperación posterior;
- 100 finalizaciones y 100 notificaciones exactamente una vez, incluso tras reinicio;
- 1.000 reconexiones con snapshot/deltas ordenados, sin huecos ni duplicados.

El resultado es JSON y retorna distinto de cero ante cualquier inconsistencia. Una ejecución del
commit `a271ea5afea2beb7b356358b8a55f50dc104c180` produjo `PASS` en 1,626 s, 704 eventos,
cero duplicados, cero estados fantasma y cero crashes.

## Evidencia física obligatoria

El runner acelerado no sustituye 72 horas de uso real. Para cerrar `SOAK-01` y `SOAK-02`, yo debo
usar el mismo commit en Home Edge y panel, registrar comienzo/fin UTC y conservar:

1. health/metrics continuos durante 72 horas sin reiniciar contadores;
2. 1.000 reconexiones de red reales, 500 cambios sobre la luz física y 100 timers del scheduler
   Wyss con notificación Android;
3. pérdida de DNS/Wi-Fi, caída y recuperación de cada provider, reinicio del daemon/Home Edge/panel
   y un corte de energía controlado;
4. backup verificado, upgrade desde v1, restore y downgrade con hashes antes/después;
5. smoke de PC, Android, panel y cada integración habilitada sobre ese commit exacto.

Yo aborto y conservo logs ante crash, watchdog, estado no verificado mostrado como real, cola sin
límite o duplicación. Hardware, cuentas o decisiones ausentes quedan como bloqueo explícito y no
se reemplazan por mocks.
