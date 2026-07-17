# Operación

## Instalación

Yo uso Arch/CachyOS, Python 3.12+, PlatformIO y OpenSSL. Yo ejecuto `scripts/create_identity.sh`, completo `config/local.toml` y `.env`, y luego ejecuto `scripts/install_bridge.sh`.

## Verificación

```bash
systemctl --user status wyss-panel-bridge
journalctl --user -u wyss-panel-bridge -f
curl --cacert config/private/ca.crt https://IP-DE-LA-NETBOOK:8443/health
pio run
```

Yo verifico el panel en este orden:

1. Yo confirmo que la retroiluminación y el táctil funcionan.
2. Yo confirmo `WYSS EN LÍNEA` en la esquina superior derecha.
3. Yo toco encendido y compruebo respuesta visual inmediata.
4. Yo confirmo `verified` y un RTT menor a 150 ms.
5. Yo desconecto la Wi-Fi y compruebo rollback sin estado falso.
6. Yo pruebo una intención de riesgo B y confirmo que aparece el modal.

## Identidades y listener v2

Yo mantengo v2 desactivado hasta crear una identidad independiente por cliente. El comando muestra el token sólo en la salida de `pair` o `rotate`; yo lo copio directamente al secret store del dispositivo y no lo envío a logs ni lo guardo en el repositorio.

```bash
uv run --project bridge python tools/manage_identities.py \
  --db bridge/data/identities.sqlite3 pair \
  --client-id panel:living --capability panel.read_projection

uv run --project bridge python tools/manage_identities.py \
  --db bridge/data/identities.sqlite3 list

uv run --project bridge python tools/manage_identities.py \
  --db bridge/data/identities.sqlite3 rotate --client-id panel:living

uv run --project bridge python tools/manage_identities.py \
  --db bridge/data/identities.sqlite3 revoke --client-id panel:living
```

Yo habilito el listener sólo con `[protocol_v2] enabled = true`. El cliente usa `X-Wyss-Client` y `Authorization: Bearer`; una revocación se relee en cada mensaje y corta la sesión inmediatamente. El primer `session.hello` entrega snapshot, o deltas posteriores a `last_event_id` cuando el cursor es válido.

Para rollback pongo `enabled = false` y reinicio el bridge. `/v1/panel` permanece registrado y las bases de identidad/eventos no se borran ni migran durante este rollback.

La migración de luces tiene un gate independiente. Yo habilito `lights_enabled = true` sólo después
del smoke de las entidades configuradas. Para volver al camino estable sin apagar el listener v2,
pongo `lights_enabled = false` y reinicio: `home.command` queda rechazado, `/v1/panel` vuelve al
gateway compatible y las bases de identidad, eventos, proyecciones y `light_audit_db` permanecen
intactas. Este rollback no escribe NVS, no modifica claves Tuya y no toca el firmware estable.

Antes de habilitarlo, cada identidad recibe únicamente su capacidad correspondiente:
`panel.light.fast`, `android.light.fast` o `pc.light.fast`. Una identidad sin esa capacidad puede
leer su proyección pero no ejecutar luces.

La conversación tiene un gate separado: `conversation_enabled = true`. Cada superficie recibe
capacidad mínima para enviar (`panel|android|pc.submit_intent`) y responder
(`panel|android|pc.answer_plan`). El bridge serializa la sesión compartida, pero Wyss sigue siendo
la única autoridad de plan, política, ejecución e historial completo. Si una aprobación no incluye
`CONFIRMAR`, venció, perdió la revisión CAS o Wyss no acredita `policy_reevaluated = true`, falla
cerrada.

Para rollback perceptual pongo `conversation_streaming = false`: se siguen enviando respuestas
completas y se mantiene exactamente la misma confirmación. Para rollback del funnel pongo
`conversation_enabled = false`; para volver además al transporte v1 recompilo con
`WYSS_PROTOCOL_V2_CLIENT=0`. Ninguno de esos pasos escribe NVS ni elimina las bases existentes.

Voz tiene un tercer gate: `voice_enabled = true`. Antes de activarlo emparejo cada cliente con
`pc.voice` o `android.voice` además de su capacidad `submit_intent`, y cierro O-01 con una ADR del
motor STT local elegido. Mientras O-01 siga abierta, el adapter productivo falla cerrado como
`provider_unavailable`; no existe un proveedor remoto implícito.

El cliente responsive vive en `/v2/voice/`. Captura sólo mientras el control está sostenido,
transcribe mediante `POST /v2/voice/transcribe`, deja editar el resultado y exige otro gesto sobre
“Enviar a Wyss”. Ese envío usa `POST /v2/voice/intent`, valida el mismo envelope
`assistant.intent` y entra al mismo `ConversationService`; no crea otra autoridad. Los tokens se
guardan sólo en `sessionStorage` de la pestaña. El endpoint limita formatos, tamaño y tiempo,
responde con `Cache-Control: no-store` y borra el buffer mutable en un `finally`.

Para rollback pongo `voice_enabled = false`: el botón de micrófono queda desactivado y el editor de
texto sigue operativo. No borro identidades ni conversación y no envío audio al event log,
proyecciones o WebSocket de control.

Spotify tiene un gate independiente: `spotify_enabled = true` sólo carga si
`spotify_approved_scopes` coincide exactamente con `user-read-playback-state`,
`user-modify-playback-state`, `user-library-read` y `user-library-modify`. O-07 debe registrar la
aprobación antes de activarlo. Los tokens OAuth viven únicamente en Wyss; Home Edge usa su canal
interno autenticado y el panel recibe sólo estado sanitizado.

Cada identidad controladora necesita `panel|android|pc.spotify.control`. Para rollback pongo
`spotify_enabled = false` y reinicio el bridge: `capability.command` queda rechazado, la proyección
Spotify queda vacía y v1, health, luces, conversación y el shell continúan. No revoco ni modifico
OAuth desde este repositorio; esa operación pertenece a Wyss.

La proyección materializada vive en `projection_db`. Si un cliente no puede aplicar deltas de forma confiable, activo temporalmente `snapshot_fallback = true`; el Edge continúa derivando la vista desde el event log y el cliente nunca escribe estado autoritativo.

## Recuperación

Yo conservo el respaldo original ya verificado con SHA-256 `842e75471b532f343886b6cf597e1ea57e8e807d55d48242157a53737628a7da`. Yo no lo publico porque puede contener datos específicos de la placa.

Yo restauro por USB sólo si el firmware no inicia. Yo no activo eFuses de seguridad hasta completar las pruebas de recuperación y conservar dos copias verificadas del respaldo.
