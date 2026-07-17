# Protocolo WSS v1

Yo intercambio JSON UTF-8 compacto por `wss://<netbook>:8443/v1/panel`. Yo autentico el handshake con `Authorization: Bearer <token>` y `X-Wyss-Panel: <id>`.

## Panel → puente

```json
{"v":1,"type":"command.fast","id":"panel-120-1","entity_id":"light.living","action":"set_brightness","brightness":72,"sent_at_ms":120}
```

```json
{"v":1,"type":"intent.submit","id":"panel-250-2","text":"Prepará el living para una película","sent_at_ms":250}
```

```json
{"v":1,"type":"plan.answer","plan_id":"pending-42","accepted":true,"risk":1}
```

## Puente → panel

Yo envío `state.snapshot`, `state.changed`, `plan.proposed`, `execution.update` y `error`. Yo incremento `revision` con un reloj monótono y hago que el panel reconcilie el estado optimista sólo con una revisión real.

```json
{"v":1,"type":"state.changed","device":{"entity_id":"light.living","friendly_name":"Living","available":true,"on":true,"brightness":72,"revision":99142}}
```

```json
{"v":1,"type":"execution.update","id":"panel-120-1","state":"verified","message":"Yo verifiqué el cambio","round_trip_ms":37}
```

Yo mantengo los identificadores idempotentes por sesión y rechazo versiones, tipos y tamaños desconocidos.

Yo envío `expires_in_ms` dentro de `plan.proposed`. Yo convierto esa duración al reloj monotónico del ESP32 y evito mezclar el reloj de la netbook, el del panel y las zonas horarias. Yo limito la confirmación a cinco minutos como máximo.

## Compatibilidad v2

El runtime v1 de esta página continúa activo y no importa contratos v2. El contrato futuro está
aislado en [Wyss Home Protocol v2](contracts/PROTOCOL_V2.md), con schema cerrado y fixtures dorados
compartidos por Python y C++. Desactivar o retirar esos archivos no modifica el listener `/v1/panel`.
