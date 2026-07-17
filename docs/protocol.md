# Transporte WSS del panel

El firmware de producción usa Wyss Home Protocol v2 por
`wss://<netbook>:8443/v2/client`, subprotocolo `wyss-v2`. Yo autentico con
`Authorization: Bearer <token>` y `X-Wyss-Client: <id>`, envío `session.hello` con el último
`event_id` aplicado y recibo snapshot o deltas ordenados. Intenciones, luces y respuestas de plan
usan los mismos envelopes cerrados que PC y Android; el contrato completo está en
[Wyss Home Protocol v2](contracts/PROTOCOL_V2.md).

`WYSS_PROTOCOL_V2_CLIENT=1` activa este cliente en producción. Para rollback compilo el mismo
firmware con `WYSS_PROTOCOL_V2_CLIENT=0`: conserva la configuración NVS y vuelve al transporte v1
descrito abajo.

## Compatibilidad WSS v1

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

## Compatibilidad

El bridge mantiene `/v1/panel` para rollback y fixtures dorados. El cliente v2 no reescribe
`bridge_url`, token, `panel_id`, CA ni ninguna otra clave NVS al cambiar de build.
