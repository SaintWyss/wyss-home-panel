# Contrato Wyss Home Protocol v2

## Objetivo

Yo defino un contrato versionado entre Wyss, Home Edge y ESP32. Yo separo comandos, eventos y proyecciones para mantener idempotencia, compatibilidad y observabilidad.

## Transporte

- Yo uso WSS con TLS para Panel ↔ Home Edge.
- Yo uso el IPC local existente de Wyss o un adapter autenticado local para Home Edge ↔ Wyss.
- Yo uso mensajes JSON UTF-8 compactos y limito tamaño, profundidad y frecuencia.
- Yo uso heartbeat, backoff exponencial con jitter y reanudación por `last_event_id`.
- Yo no envío audio, imágenes de cámara ni secretos sobre este canal de control.

## Envelope

```json
{
  "v": 2,
  "type": "command.requested",
  "message_id": "01J...",
  "correlation_id": "01J...",
  "causation_id": "01J...",
  "source": "panel:living",
  "sent_at": "2026-07-17T12:00:00Z",
  "payload": {}
}
```

Yo requiero `v`, `type`, `message_id`, `source` y `payload`. Yo uso ULID/UUIDv7 para unicidad, pero no ordeno estados de hardware mediante hora de clientes.

## Handshake

```json
{"v":2,"type":"session.hello","message_id":"...","source":"panel:living","payload":{"firmware":"2.0.0","capabilities":["ui.core","light.fast","dashboard"],"last_event_id":812}}
```

```json
{"v":2,"type":"session.welcome","message_id":"...","source":"edge:home","payload":{"session_id":"...","heartbeat_ms":12000,"max_message_bytes":8192,"snapshot_required":false}}
```

Yo rechazo versiones incompatibles con un error explícito y conservo compatibilidad v1 durante una ventana de migración de una release.

## Comandos

### Acción rápida de luz

```json
{
  "v":2,
  "type":"home.command",
  "message_id":"...",
  "source":"panel:living",
  "payload":{
    "request_id":"...",
    "idempotency_key":"panel:living:9231",
    "entity_id":"light.living",
    "action":"set_brightness",
    "value":72,
    "expected_revision":91
  }
}
```

Yo permito este path sólo a entidades allowlisted y acciones A. Yo rechazo valores fuera de dominio, revisiones imposibles y keys repetidas con payload distinto.

`turn_on`, `turn_off` y `toggle` no admiten parámetros. `set_brightness` usa `value` entre 0 y
100; `set_color` usa `rgb` entre `0x000000` y `0xFFFFFF`; `activate_scene` exige una entidad
`scene.*`. Python y firmware validan exactamente las mismas combinaciones y rechazan campos
sobrantes. El resultado verificado publica la lista completa de entidades de hogar para que todos
los clientes converjan sobre la misma revisión.

### Intención

```json
{"v":2,"type":"assistant.intent","message_id":"...","source":"android:owner","payload":{"request_id":"...","text":"Prepará el living para estudiar","input":"voice"}}
```

Yo envío texto revisable, no audio. Yo trato el contenido como no confiable hasta que Wyss lo convierta en Plan y lo evalúe.

La captura PTT usa un endpoint binario separado y autenticado; el audio crudo nunca forma parte del
envelope, event log, proyección ni historial. Transcribir no envía una intención. Sólo después de
editar y pulsar “Enviar a Wyss”, PC o Android publica este `assistant.intent` con `input = voice`.
El endpoint HTTP reutiliza el mismo parser estricto y el mismo `ConversationService` que WSS.

### Respuesta a plan

```json
{"v":2,"type":"plan.answer","message_id":"...","source":"android:owner","payload":{"plan_id":"...","decision":"approve","confirmation":"CONFIRMAR","expected_revision":3}}
```

Yo hago que Wyss reevalúe la política antes de ejecutar. Yo respondo `already_resolved` si otro cliente cerró el plan.

`assistant.intent` admite exactamente `request_id`, `text` (1–1.000 caracteres no blancos) e
`input` (`text` o `voice`). `plan.answer` admite exactamente `plan_id`, `decision`,
`confirmation` y `expected_revision`; aprobar exige la cadena exacta `CONFIRMAR`. Home Edge
serializa una sola sesión visible, deja ganar a la primera respuesta válida y exige que Wyss
devuelva `policy_reevaluated = true`. B/C no se ejecutan sin ese circuito y D nunca crea un pending
confirmable.

### Control de media y temporizadores

```json
{"v":2,"type":"capability.command","message_id":"...","source":"panel:living","payload":{"capability":"spotify","action":"next","idempotency_key":"..."}}
```

```json
{"v":2,"type":"capability.command","message_id":"...","source":"android:owner","payload":{"capability":"timer","action":"create","duration_seconds":900,"label":"Descanso"}}
```

Yo enruto estas acciones por Wyss. Yo no hago que el panel conozca endpoints o tokens de proveedores.

## Eventos

Yo publico al menos:

- `assistant.state.changed`;
- `assistant.response.delta` y `assistant.response.completed`;
- `plan.proposed`, `plan.resolved` y `execution.updated`;
- `home.entity.changed`;
- `spotify.state.changed`;
- `weather.forecast.changed`;
- `calendar.agenda.changed`;
- `reminder.changed`;
- `timer.changed` y `timer.completed`;
- `camera.state.changed`;
- `notification.delivered`;
- `system.health.changed`.

Ejemplo:

```json
{"v":2,"type":"home.entity.changed","message_id":"...","source":"edge:home","payload":{"entity_id":"light.living","revision":92,"available":true,"on":true,"brightness":72,"verified":true}}
```

## Snapshot

Yo envío `projection.snapshot` al conectar, al detectar hueco o al cambiar una versión de schema. Yo limito el snapshot a datos de presentación actuales; yo no envío historial completo, secretos ni audit log al ESP32.

El Home Edge materializa esta vista sólo desde el event log ordenado. Un reducer rechaza huecos globales y revisiones obsoletas; un replay exacto no vuelve a aplicar estado. Los cursores por cliente y las claims de idempotencia están acotados, mientras los eventos durables no se eliminan junto con su cache temporal. `snapshot_fallback = true` fuerza snapshots periódicos sin convertir a los clientes en autoridad.

```json
{
  "v":2,
  "type":"projection.snapshot",
  "message_id":"...",
  "source":"edge:home",
  "payload":{
    "projection_version":1204,
    "assistant":{"state":"sleeping","message":""},
    "home":{"entities":[]},
    "spotify":{},
    "weather":{"days":[]},
    "agenda":{"next":[]},
    "reminders":{"items":[]},
    "timers":{"items":[]},
    "cameras":[]
  }
}
```

## Errores

Yo uso códigos cerrados y mensajes accionables:

- `unauthenticated`, `forbidden`, `device_revoked`;
- `unsupported_version`, `invalid_message`, `message_too_large`;
- `rate_limited`, `conflict`, `already_resolved`;
- `provider_unavailable`, `entity_unavailable`, `timeout`;
- `policy_rejected`, `confirmation_required`;
- `snapshot_required`, `internal_error`.

Yo no devuelvo stack traces, tokens, claves, URLs con credenciales ni detalles de red innecesarios.

## Compatibilidad

Yo aplico cambios aditivos dentro de v2. Yo ignoro campos desconocidos y rechazo tipos desconocidos sólo cuando afectan seguridad. Yo incremento versión mayor si cambio semántica, autenticación o campos obligatorios. Yo mantengo fixtures dorados entre C++ y Python y pruebo compatibilidad cruzada en CI.

## Límites

| Control | Valor inicial que yo fijo |
| --- | --- |
| Mensaje control | 8 KiB |
| Profundidad JSON | 8 |
| Intent text | 1.000 caracteres |
| Acciones rápidas | 12/s por panel y 4/s por entidad |
| Comandos personales | 4/s por owner |
| Cache idempotencia | 24 h en servidor; 256 recientes en sesión ESP |
| Heartbeat | 12 s; timeout después de 2 pérdidas |
| Reconnect | 1–30 s con jitter |
| Confirmación | TTL asignado por Wyss, máximo 5 min en panel |

## Contract tests

Yo genero fixtures canónicos y los consumo en Python y C++. Yo pruebo mensajes válidos, campos extra, límites, replay, duplicados, revisión atrasada, versión incompatible y payloads maliciosos. Yo no fusiono un cambio de contrato sin actualizar fixtures, documentación y tests de ambos repos.
