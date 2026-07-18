# Catálogo de integraciones

## Estrategia

Yo implemento cada capacidad detrás de un port pequeño y un adapter reemplazable. Yo mantengo secretos en la netbook, scopes mínimos, health independiente, cache explícito y contract tests. Yo no creo un repositorio por integración.

## Luces

**Autoridad:** Home Edge.

**Adapter inicial:** Tuya LAN 3.3 proveniente del baseline probado.

**Port:** `LightPort.snapshot()` y `LightPort.execute(command)`.

Yo conservo encendido, brillo, color, escenas y estado real. Yo serializo acciones por foco,
reintento sólo operaciones idempotentes y hago rollback visual en 2,5 s. Tuya acepta varias luces
y escenas declarativas con DPS configurables; Home Assistant implementa el mismo port sin hacer que
el dominio dependa de ninguno. Cada comando se registra en un journal SQLite privado antes de
publicar su proyección verificada.

## Spotify Premium

**Autoridad:** Wyss.

**Adapter:** Spotify Web API.

**Ports:** `MediaQueryPort`, `MediaControlPort`, `OAuthCredentialPort`.

Yo implemento OAuth Authorization Code con PKCE o intercambio server-side, refresh seguro, revocación y scopes mínimos. Yo necesito lectura del playback y modificación del playback sólo cuando el owner habilite control. Yo trato `204`, dispositivo inactivo, rate limit y token vencido como estados de dominio.

Yo incluyo reproducción actual, play/pause, anterior, siguiente, volumen, transferencia de dispositivo y playlists/favoritos seleccionados. Yo no guardo catálogo completo ni credenciales en el panel.

## Clima de Resistencia

**Autoridad externa:** Open-Meteo u otro proveedor configurado.

**Autoridad de cache:** Wyss/Home projection.

**Port:** `WeatherPort.forecast(location, days)`.

Yo fijo Resistencia, Chaco mediante coordenadas configurables y zona `America/Argentina/Cordoba`. Yo solicito actual, máxima, mínima, precipitación, viento y código meteorológico para siete días. Yo refresco en segundo plano cada 30–60 min, uso ETag/cache cuando esté disponible y muestro antigüedad.

## Google Calendar

**Autoridad:** Google Calendar.

**Adapter:** `WyssCalendarGateway` sobre la API interna autenticada de Wyss; sólo Wyss integra la
API Google Calendar y conserva OAuth.

**Ports:** `CalendarPort` y `CalendarStorePort`.

Yo uso `calendar.events.owned.readonly` para lectura o `calendar.events.owned` para escritura, nunca
ambos ni scopes más amplios. Yo consulto una ventana semanal incremental mediante sync token,
manejo paginación, recurrencia, timezone y eventos all-day, y recupero cursores inválidos mediante
resync atómico. Home Edge persiste sólo agenda sanitizada y cursor opaco.

Yo convierto crear, editar y eliminar en planes de Wyss. Yo clasifico lectura como A, creación/edición normal como B y eliminaciones o cambios masivos como C; la política real conserva la última palabra.

## Recordatorios

**Autoridad:** scheduler/memory de Wyss.

**Port:** `ReminderPort`.

Yo represento recordatorios como objetos propios con `id`, texto, vencimiento, recurrencia, estado y canales. Yo puedo vincularlos a un evento, pero no los hago depender del mecanismo de reminders de un proveedor. Yo notifico en Android y proyecto estado en pantalla.

## Temporizadores

**Autoridad:** scheduler durable de Wyss.

**Port:** `TimerPort`.

Yo uso deadline monotónico para ejecución y timestamp UTC para recuperación. Yo persisto antes de confirmar creación, sobrevivo reinicios, evito duplicar finalizaciones mediante idempotencia y publico `timer.completed` una vez. Yo notifico Android y despierto el panel visualmente.

## Voz PC y Android

**Autoridad:** Wyss.

**Ports:** `SpeechCapturePort` en cliente y `TranscriptionPort` en servidor.

Yo capturo sólo con botón. Yo priorizo transcripción local en PC; yo uso la misma API desde Android cuando el hardware/permiso lo permita. Yo siempre muestro texto editable antes de enviar. Yo mando al panel sólo estados y texto final.

Yo dejo TTS fuera de v2.0.0 porque el owner pidió respuesta escrita. Yo conservo un `SpeechOutputPort` sin adapter activo para evolución futura.

## Notificaciones Android

**Autoridad:** Wyss.

**Adapter:** cliente Android/Capacitor con canal de notificación y entrega autenticada.

Yo notifico temporizadores y recordatorios aunque la pantalla esté dormida. Yo uso IDs deterministas para deduplicar, categorías separadas, deep links y acciones seguras. Yo nunca agrego botón de confirmación C directamente en una notificación sin abrir el gate completo.

## Cámaras

**Estado:** yo difiero el adapter hasta recibir marca/modelo.

**Contrato reservado:** `CameraPort.list()`, `snapshot(id)` y `health(id)`.

Yo prefiero ONVIF/RTSP o endpoint snapshot local. Yo hago que Home Edge obtenga y autentique el stream; yo no entrego credenciales al ESP32. Yo genero un snapshot dimensionado y de corta vida para la pantalla. Yo no expongo cámaras a Internet ni grabo por defecto.

## Red remota

Yo mantengo LAN TLS como default. Si necesito control fuera de casa, yo uso una red privada Tailscale/WireGuard con ACL por dispositivo. Yo no uso port forwarding, UPnP ni un relay público propio en v2.0.0.

## Matriz de aislamiento

| Falla | Módulos que yo permito afectar |
| --- | --- |
| Spotify | Sólo Media |
| Google OAuth | Agenda/recordatorios sincronizados, no timers locales |
| Open-Meteo | Sólo pronóstico nuevo; yo conservo cache |
| Tuya | Hogar, no conversación ni agenda |
| Push Android | Entrega móvil; yo mantengo alerta en panel y estado pending |
| Cámara | Sólo esa cámara; yo no bloqueo otras capacidades |

## Referencias normativas y técnicas

Yo baso la implementación en documentación primaria y vuelvo a verificarla al iniciar cada adapter:

- [Spotify Authorization Code con PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [Spotify playback state](https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback)
- [Spotify playback control](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback)
- [Google Calendar API](https://developers.google.com/workspace/calendar/api/guides/overview)
- [Google Calendar incremental sync](https://developers.google.com/workspace/calendar/api/guides/sync)
- [Google Calendar create events](https://developers.google.com/workspace/calendar/api/guides/create-events)
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- [Capacitor Local Notifications](https://capacitorjs.com/docs/apis/local-notifications)
- [Waveshare ESP32-S3-Touch-LCD-7](https://docs.waveshare.com/ESP32-S3-Touch-LCD-7)
