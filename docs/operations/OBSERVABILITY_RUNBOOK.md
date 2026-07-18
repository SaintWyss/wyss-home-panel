# Runbook de observabilidad

## Acceso mínimo

La exportación está desactivada por defecto. Para habilitarla, el operador configura
`observability_enabled = true`, empareja una identidad de operaciones con capacidad exclusiva
`ops.read_metrics` y consulta `GET /v2/ops/metrics` por el canal TLS privado. Una identidad de
panel ordinaria recibe 403.

La respuesta sólo contiene nombres internos acotados, duración, error, health y
`correlation_id`. Nunca debe contener headers, cuerpos, intención, audio, SSID, IP doméstica,
OAuth, token, clave Tuya ni credencial de cámara. Una correlación que no respete el formato seguro
se reemplaza por `redacted`.

## Diagnóstico

1. Ejecutar `python tools/doctor.py --format json` y conservar el resultado ligado al commit.
2. Consultar `/health`; si falla, no intentar reprovisionar ni cambiar NVS.
3. Consultar `/v2/ops/metrics` y revisar por operación `count`, `errors`, `p50_ms`, `p95_ms` y
   `p99_ms`.
4. Correlacionar por ID entre cliente, Edge y Wyss. No buscar texto o payload del usuario.
5. Si una conexión en bootstrap cierra con 4413, investigar cliente lento: el Edge cerró por
   backpressure antes de permitir crecimiento ilimitado.

## Alertas iniciales

- `health=down`: aislar el módulo inmediatamente.
- `health=degraded`: conservar cache explícita y verificar antigüedad.
- errores >5 % con al menos 20 muestras: revisar proveedor y autenticación.
- p95 superior al presupuesto documentado durante tres ventanas: capturar evidencia y aislar el
  proveedor; no ampliar colas.
- cierre 4413 repetido: actualizar o revocar el cliente lento.

## Aislamiento y rollback

Deshabilitar sólo el feature flag no crítico afectado (`spotify_enabled`, `weather_enabled`,
`calendar_enabled`, `reminders_enabled`, `timers_enabled` u `observability_enabled`), reiniciar
Home Edge y comprobar `/health` y luz local. No borrar cache, identidades ni outbox durante el
diagnóstico. Si el problema persiste, volver al commit anterior verificado; OTA física sigue su
propio gate de firma y health.

La luz y el listener v1 son el health básico. Cámaras y VPN no tienen procedimiento hasta cerrar
O-03 y O-02 respectivamente.
