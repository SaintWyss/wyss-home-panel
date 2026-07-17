# Wyss Home v2.0.0 — visión y requisitos del producto final

## Visión

Yo convierto la pantalla Waveshare ESP32-S3-Touch-LCD-7 en la presencia física de Wyss dentro del hogar. Yo quiero una experiencia de clase Jarvis, pero con identidad visual propia: Wyss entiende instrucciones desde PC o Android, aplica su política, sincroniza el estado y usa la pantalla para responder, confirmar y controlar el entorno con latencia perceptual cero.

Yo no construyo una botonera aislada ni un segundo asistente. Yo extiendo el Wyss existente con un nuevo cliente físico y un edge doméstico seguro.

## Resultado final

Yo considero terminado Wyss Home v2.0.0 cuando puedo:

1. hablar mediante un botón desde Android o PC y recibir la respuesta escrita en la pantalla;
2. escribir desde Android, PC o pantalla y observar una conversación coherente en todos los clientes;
3. controlar luces con respuesta visual inmediata y ver el estado real reconciliado;
4. controlar Spotify Premium y ver reproducción, artista, progreso y dispositivo activo;
5. consultar el clima de siete días para Resistencia, Chaco;
6. consultar, crear, modificar y eliminar eventos y recordatorios de Google Calendar con política y confirmación;
7. crear, pausar, cancelar y finalizar temporizadores, con notificación en Android;
8. mostrar cámaras y snapshots de manera segura después de validar el hardware exacto;
9. entrar automáticamente en modo “Wyss durmiendo”, despertar por toque o evento y conservar fluidez;
10. continuar controlando luces en modo degradado cuando los servicios no críticos fallen;
11. instalar, actualizar y recuperar el sistema sin perder configuración ni el respaldo de fábrica;
12. demostrar seguridad, rendimiento, accesibilidad, estabilidad y trazabilidad mediante evidencia reproducible.

## Personas y superficies

Yo diseño para un único owner autenticado, Santiago, y para tres superficies:

- **Wyss PC:** yo lo uso como autoridad, executor, reconocimiento de voz y centro operativo.
- **Wyss Android:** yo lo uso como micrófono push-to-talk, control remoto, confirmación y receptor de notificaciones.
- **Wyss Home Panel:** yo lo uso como presencia ambiental, dashboard y control táctil de baja latencia.

Yo no incluyo multiusuario, invitados ni exposición pública a Internet en v2.0.0.

## Principios no negociables

- Yo conservo a `SaintWyss/Wyss` como única autoridad de identidad, planes, riesgo y auditoría.
- Yo hago que el LLM proponga y que la política determinista A–D decida.
- Yo hago que toda acción B/C pase por confirmación y que D no tenga bypass.
- Yo uso un único camino de ejecución aunque la orden venga de PC, Android o pantalla.
- Yo respondo visualmente antes de esperar la red sólo para acciones reversibles y autorizadas.
- Yo no guardo tokens de Spotify, Google ni cámaras dentro del firmware.
- Yo no abro puertos del router; para acceso remoto yo uso una VPN personal autenticada.
- Yo degrado de forma explícita: nunca muestro como verificado un cambio no confirmado.
- Yo asigno una sola fuente de verdad a cada dato.
- Yo priorizo una interfaz estable sobre efectos visuales costosos.

## Requisitos funcionales

### RF-01 — Conversación multicliente

Yo envío voz transcripta o texto a la misma sesión del owner. Yo publico estados `idle`, `listening`, `thinking`, `awaiting_confirmation`, `executing`, `verified` y `failed`. Yo muestro la respuesta final en la pantalla y mantengo el historial completo en Wyss, no en el ESP32.

### RF-02 — Push-to-talk

Yo inicio y finalizo grabación sólo mediante un botón visible en Android o PC. Yo muestro permiso, captura, transcripción editable y envío explícito. Yo nunca activo escucha permanente ni palabra de activación en v2.0.0.

### RF-03 — Luces

Yo conservo el control Tuya LAN 3.3 probado. Yo permito encendido, apagado, brillo, color, escenas y temporizador. Yo aplico estado optimista y reconcilio con el estado real dentro del presupuesto de latencia.

### RF-04 — Spotify

Yo vinculo una cuenta Premium mediante OAuth con PKCE o flujo autorizado por servidor. Yo muestro reproducción actual, artista, progreso, dispositivo y disponibilidad. Yo permito play/pause, anterior, siguiente, volumen, dispositivo y playlists favoritas según los scopes mínimos.

### RF-05 — Clima

Yo muestro condición actual y siete días para Resistencia, Chaco. Yo cacheo el último pronóstico válido, indico antigüedad y mantengo la pantalla útil si el proveedor falla.

### RF-06 — Google Calendar y recordatorios

Yo muestro agenda diaria/semanal y próximo evento. Yo creo, edito y elimino eventos sólo mediante Wyss y su política. Yo trato recordatorios como objetos durables y notificables; yo no confundo un recordatorio con una ejecución autónoma.

### RF-07 — Temporizadores

Yo mantengo temporizadores en el servidor usando reloj monotónico y persistencia durable. Yo sincronizo su estado con todos los clientes y envío una notificación Android al finalizar. Yo recupero temporizadores después de reiniciar.

### RF-08 — Cámaras

Yo reservo el contrato de cámaras desde el inicio. Yo implemento snapshots, disponibilidad y vista completa sólo después de identificar modelo, autenticación y protocolo. Yo no declaro v2.0.0 final hasta completar el smoke físico o excluir formalmente cámaras mediante una nueva decisión del owner.

### RF-09 — Modo dormido

Yo muestro un núcleo de baja frecuencia visual, hora, clima y próximo evento con brillo reducido. Yo despierto por toque, orden, confirmación o alerta. Yo regreso al reposo después de inactividad configurable sin cortar la conexión.

### RF-10 — Modo manual

Yo presento un shell Wyss Core oscuro/cian con navegación consistente. Yo agrupo módulos por intención y no por proveedor. Yo mantengo objetivos táctiles de al menos 44 px y evito scroll crítico.

### RF-11 — Sincronización

Yo distribuyo cambios como eventos versionados. Yo uso snapshot al conectar y deltas después. Yo resuelvo repetición con idempotencia, orden con revisión monotónica por agregado y reconexión con cursor.

### RF-12 — Actualización y recuperación

Yo soportaré actualización firmada y rollback de firmware. Yo mantengo carga USB como camino de rescate. Yo conservo y verifico el respaldo de fábrica fuera del repositorio.

## Requisitos no funcionales

| Id | Objetivo final que yo acepto |
| --- | --- |
| RNF-01 Latencia táctil | Yo pinto feedback local en ≤50 ms p95 y mantengo el ciclo LVGL estable. |
| RNF-02 Acción local | Yo verifico luces en ≤150 ms p95 dentro de LAN saludable. |
| RNF-03 Fluidez | Yo mantengo ≥30 FPS durante interacción y reduzco deliberadamente a 5–10 FPS en reposo. |
| RNF-04 Arranque | Yo muestro UI útil en ≤5 s y estado sincronizado en ≤10 s p95. |
| RNF-05 Disponibilidad | Yo mantengo luces manuales disponibles aunque fallen Spotify, Calendar o clima. |
| RNF-06 Seguridad | Yo uso TLS, identidad por dispositivo, scopes mínimos, rotación y revocación. |
| RNF-07 Privacidad | Yo no conservo audio crudo por defecto y yo redacto secretos de logs y auditoría. |
| RNF-08 Resiliencia | Yo supero 72 h de soak, 1.000 reconexiones y cortes de red/energía sin estado falso. |
| RNF-09 Recursos | Yo mantengo RAM <75 %, Flash <80 % y margen de OTA documentado. |
| RNF-10 Mantenibilidad | Yo hago cumplir arquitectura con tests de dependencias, contratos y ADR. |
| RNF-11 Accesibilidad | Yo garantizo contraste AA equivalente, texto legible y controles táctiles consistentes. |
| RNF-12 Sostenibilidad | Yo evito polling agresivo, limito brillo y mido consumo y tráfico de red. |

## Fuera de alcance v2.0.0

Yo excluyo escucha permanente, reconocimiento de voz dentro del ESP32, multiusuario, marketplace de plugins, ejecución de código de terceros, exposición pública, video de múltiples cámaras a alta tasa, cloud obligatorio y automatizaciones que confirmen por el owner.

## Criterio de aceptación final

Yo no uso la palabra “final” por cantidad de código. Yo la uso únicamente cuando la matriz de trazabilidad esté completa, CI esté verde, el firmware esté instalado en la placa real, Android y PC hayan pasado smoke, las integraciones reales hayan sido verificadas, la recuperación haya sido ensayada y los límites conocidos estén documentados.
