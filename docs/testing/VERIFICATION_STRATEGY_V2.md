# Estrategia de verificación Wyss Home v2.0.0

## Filosofía

Yo demuestro comportamiento por capa y después end-to-end. Yo no reemplazo pruebas físicas con mocks ni declaro fluidez a partir de compilación. Yo conservo evidencia por commit y hago que cada requisito tenga test o smoke asociado.

## Pirámide

### Dominio

Yo pruebo política del borde, reducers de proyección, máquinas de estado, expiración, idempotencia, resolución de conflictos, timers y degradación como funciones puras. Yo uso clocks y UUID fakes.

### Contratos

Yo comparto fixtures JSON v2 entre Python y C++. Yo pruebo compatibilidad, campos desconocidos, límites, duplicados, replay, revisión, snapshots y errores.

### Adapters

Yo uso servidores falsos para Spotify, Google, Open-Meteo, push y cámaras. Yo pruebo OAuth refresh, 401, 403, 404, 429, 5xx, timeout, malformed JSON, pagination/sync token y cancelación.

Yo pruebo Tuya contra fake protocol y contra el foco real en smoke separado. Yo no ejecuto integraciones con secretos en CI público.

### Componentes UI

Yo pruebo navegación, estados visuales, tamaño táctil, textos largos, offline y confirmaciones en simulador LVGL. Yo uso screenshot golden con tolerancia controlada y reviso cambios visuales intencionalmente.

### Integración

Yo levanto Wyss fake + Home Edge + firmware native/simulado. Yo pruebo reconexión, snapshot+deltas, acción optimista, rollback, dos clientes confirmando y módulos fallando de manera independiente.

### Hardware-in-the-loop

Yo uso la Waveshare exacta N16R8 y el foco LEDVANCE real. Yo mido tacto→paint, comando→verificación, FPS, heap, temperatura, Wi-Fi y energía. Yo automatizo al menos smoke de carga/serial y conservo verificación manual de tacto y aspecto.

### End-to-end real

Yo pruebo PC, Android físico, pantalla, foco, Spotify Premium, Google Calendar, notificación y proveedor de clima en el mismo commit de release. Yo agrego cámara sólo cuando llegue el hardware.

## Matriz mínima

| Escenario | Evidencia que yo exijo |
| --- | --- |
| Voz Android → pantalla | Yo pulso, transcribo, reviso, envío y veo respuesta correcta. |
| Voz PC → pantalla | Yo repito con micrófono PC y mismo contrato. |
| Luz desde panel | Yo veo feedback ≤50 ms y verificación LAN ≤150 ms p95. |
| Luz desde Android | Yo veo panel y PC sincronizados sin polling visible. |
| Spotify | Yo controlo sesión real y recupero token vencido. |
| Clima | Yo veo siete días, cache y antigüedad sin Internet. |
| Calendar | Yo creo/edito/elimino con confirmación y sync incremental. |
| Recordatorio | Yo creo, reinicio host y recibo notificación Android. |
| Timer | Yo reinicio procesos y recibo una sola finalización. |
| Confirmación concurrente | Yo apruebo en un cliente y el segundo queda resuelto. |
| Panel offline | Yo restauro snapshot correcto sin repetir acciones. |
| Wyss offline | Yo mantengo luz local A y bloqueo capacidades personales. |
| OTA fallida | Yo arranco partición anterior y conservo configuración. |
| Revocación | Yo revoco Android/panel y verifico rechazo inmediato. |

## Rendimiento

Yo recolecto al menos 1.000 muestras por flujo crítico y reporto p50, p95 y p99. Yo mido:

- tacto→primer píxel;
- LVGL handler y touch handler;
- acción→ack Edge;
- acción→estado real;
- intent→primer estado `thinking`;
- respuesta→paint;
- reconnect→snapshot aplicado;
- RAM/heap mínimo y fragmentación;
- tráfico por hora en idle;
- consumo con brillo activo y dormido.

## Resiliencia

Yo ejecuto soak de 72 h, 1.000 reconexiones, 500 cambios de brillo, 100 timers, caída de cada provider, pérdida de DNS, cambio de IP, reinicio de daemon/Edge/panel y corte de energía. Yo rechazo leaks, deadlocks, watchdog, cola infinita, doble notificación y estado fantasma.

## Seguridad

Yo agrego fuzz de parser, mensajes >8 KiB, JSON profundo, IDs repetidos, payload alterado, tokens vencidos, CA inválida, downgrade, SSRF, race de confirmación, intents peligrosos y contenido externo con prompt injection.

## Gates por pull request

| Alcance | Gate que yo hago obligatorio |
| --- | --- |
| Dominio/ports | unit + mypy/compile + import rules |
| Protocolo | fixtures cruzados + compatibilidad |
| Adapter externo | contract + error matrix + no-secret logs |
| Firmware/UI | host tests + PlatformIO + static analysis + screenshot review |
| Seguridad | dangerous suite + threat model diff |
| Android/voz | tests + build APK + smoke físico cuando cambie permisos/audio |
| Deploy/OTA | install/upgrade/rollback en host y placa de prueba |

## Gate de release

Yo exijo commit exacto, CI completo, SBOM, checksums, firmware firmado, APK generado, configuración migrada, backups verificados, 72 h soak, matriz E2E real, recuperación ensayada, métricas dentro de presupuesto y documentación de límites. Yo no acepto “compila” como evidencia suficiente.
