# Requirements: Wyss Home Panel v2.0.0

**Defined:** 2026-07-17
**Core Value:** Toda acción doméstica debe pasar por una única autoridad de política y ejecución de Wyss, conservar coherencia observable entre clientes y fallar de forma segura.

## v2.0.0 Requirements

### Baseline y protección

- [x] **BASE-01**: El operador puede reproducir el build del firmware y los tests del Home Edge desde un checkout limpio con versiones registradas.
- [x] **BASE-02**: El operador puede validar fixtures dorados del protocolo v1 antes de introducir contratos v2.
- [x] **BASE-03**: El operador puede ejecutar un comando `doctor` que diagnostica toolchain, configuración segura y dependencias sin exponer secretos.
- [ ] **BASE-04**: El operador dispone de evidencia fechada del backup de fábrica y de las métricas físicas de latencia, memoria y Flash asociadas al commit probado.
- [ ] **BASE-05**: Cada cambio es bloqueado por CI cuando falla dominio, bridge, firmware, detección de secretos o validación documental esencial.

### Contratos y arquitectura

- [x] **ARCH-01**: Cada capacidad v2 dispone de un port pequeño y estable antes de implementar adapters reales.
- [x] **ARCH-02**: El repositorio bloquea imports que violan dominio, aplicación, ports y adapters.
- [x] **PROTO-01**: Python y C++ aceptan el mismo envelope v2 versionado y rechazan mensajes incompatibles o fuera de límites.
- [x] **PROTO-02**: Fixtures dorados compartidos prueban campos desconocidos, duplicados, replay, revisión, snapshots y errores en ambos lenguajes.
- [x] **PROTO-03**: El runtime v1 permanece operativo mientras ningún consumidor dependa exclusivamente de v2.

### Identidad y eventos

- [ ] **IDENT-01**: El operador puede emparejar, rotar y revocar cada panel o cliente mediante identidad independiente y rechazo inmediato.
- [x] **EVENT-01**: Un cliente reconectado recupera sesión mediante heartbeat, cursor, snapshot y deltas sin repetir acciones.
- [x] **EVENT-02**: El Home Edge aplica idempotencia, orden revisionado, límites de tasa y observabilidad correlacionada a todos los mensajes v2.
- [x] **EVENT-03**: La migración puede desactivar v2 y volver al listener v1 sin perder configuración ni autoridad.

### Proyección multicliente

- [ ] **SYNC-01**: Un cambio iniciado desde PC, Android o panel converge en las tres superficies sin duplicación ni polling agresivo.
- [x] **SYNC-02**: Cada agregado aplica reducers, revisión monotónica, snapshot, delta y resolución determinista de conflictos.
- [x] **SYNC-03**: Los clientes conservan únicamente proyecciones o caches acotados y nunca se convierten en autoridades mutables paralelas.

### Experiencia Wyss Core

- [x] **UI-01**: El panel presenta shell Wyss Core, modo manual, modo dormido y estados de conversación con navegación consistente.
- [ ] **UI-02**: La interacción mantiene feedback táctil ≤50 ms p95, ≥30 FPS activa, 5–10 FPS en reposo y objetivos táctiles ≥44 px.
- [x] **UI-03**: El simulador y las pruebas visuales cubren navegación, textos largos, offline, confirmaciones, contraste y cambios intencionales.

### Luces y degradación

- [ ] **LIGHT-01**: El owner controla varias luces por encendido, brillo, color, escenas y disponibilidad desde cualquier superficie mediante un único `LightPort`.
- [ ] **LIGHT-02**: El panel muestra feedback optimista reversible y reconcilia el estado real de LAN en ≤150 ms p95 bajo condiciones saludables.
- [ ] **LIGHT-03**: Las luces manuales autorizadas continúan disponibles cuando fallan servicios no críticos, Wi-Fi se recupera o una entidad queda offline.

### Conversación y voz

- [ ] **CONV-01**: Texto enviado desde PC, Android o panel usa una sesión coherente y proyecta `idle`, `thinking`, confirmación, ejecución, verificación y fallo.
- [ ] **CONV-02**: Acciones B/C exigen confirmación válida con TTL y carrera segura; acciones D no tienen bypass y toda confirmación reevalúa política.
- [ ] **VOICE-01**: El owner captura voz sólo mientras mantiene pulsado un control visible en PC o Android, edita la transcripción y envía explícitamente.
- [ ] **VOICE-02**: El sistema maneja permisos negados, silencio, ruido, interrupción y proveedor caído, y elimina el audio crudo por defecto.

### Integraciones personales

- [ ] **MEDIA-01**: El owner vincula Spotify Premium con scopes mínimos, ve playback/dispositivo y controla play, pausa, pista, volumen y favoritos desde cualquier superficie.
- [ ] **MEDIA-02**: Spotify recupera expiración, 204, 401, 429 y dispositivo inactivo sin exponer tokens a clientes.
- [ ] **WEATHER-01**: El panel muestra condición actual y siete días para Resistencia, Chaco, con timezone correcto, antigüedad y cache offline explícito.
- [ ] **CAL-01**: El owner consulta agenda diaria/semanal y crea, edita o elimina eventos mediante Wyss, policy y confirmación.
- [ ] **CAL-02**: Calendar maneja scopes separados, sync incremental, paginación, recurrencia, all-day, timezone y token invalidado.
- [ ] **REM-01**: El owner crea recordatorios durables, recurrentes, completables y posponibles que sobreviven reinicios.
- [ ] **REM-02**: Android entrega una única notificación recuperable con permisos, deduplicación y deep link, sin perder el recordatorio si push falla.
- [ ] **TIMER-01**: El owner crea, pausa, reanuda y cancela timers durables y presets desde cualquier superficie.
- [ ] **TIMER-02**: Cada timer recupera deadline tras reinicio o ajuste de reloj y emite exactamente un `timer.completed` y una notificación Android.

### Cámaras y acceso remoto

- [ ] **CAM-01**: Tras identificar hardware y protocolo, el owner consulta disponibilidad y un snapshot efímero redimensionado de una cámara sin retención ni secretos en firmware.
- [ ] **CAM-02**: El adapter de cámara rechaza credenciales inválidas, timeout, SSRF y destinos no autorizados, y puede deshabilitarse sin afectar el shell.
- [ ] **REMOTE-01**: El owner controla el sistema fuera de la LAN únicamente por Tailscale o WireGuard con ACL y DNS privados por dispositivo.
- [ ] **REMOTE-02**: Revocación, pérdida de VPN y rollback vuelven a LAN-only sin listeners públicos ni port forwarding.

### Actualización y operación

- [ ] **OTA-01**: El operador instala firmware firmado con particiones A/B, health boot y rollback ante imagen corrupta, firma inválida o corte de energía.
- [ ] **OTA-02**: Provisioning, migración, backup, restore y rescate USB son idempotentes y conservan configuración; eFuses requieren autorización separada.
- [ ] **OBS-01**: El operador obtiene métricas y traces correlacionadas de latencia p50/p95/p99, arranque, FPS, heap, tráfico, energía y fallos por módulo.
- [ ] **OBS-02**: `doctor`, backpressure, caches acotados, alertas y runbooks aíslan fallos y no registran secretos.
- [ ] **SEC-01**: La suite adversarial cubre parser, replay, downgrade, SSRF, injection, carreras, revocación, scopes, dependencias, SBOM y secret scan.
- [ ] **SEC-02**: Ningún hallazgo crítico o alto queda abierto antes del release; los riesgos restantes tienen owner, impacto, mitigación y fecha.

### Resiliencia y release

- [ ] **SOAK-01**: El sistema supera 72 horas, 1.000 reconexiones, 500 cambios de brillo, 100 timers y fault injection sin crash, watchdog, estado fantasma o duplicación.
- [ ] **SOAK-02**: Upgrade desde v1, restore y rollback preservan datos y configuración en la matriz E2E real.
- [ ] **REL-01**: La trazabilidad alcanza 100 %, CI queda verde y cada requisito enlaza test automatizado y evidencia física cuando corresponde.
- [ ] **REL-02**: El operador publica artefactos versionados, checksums, SBOM, firmas, changelog, compatibilidad, límites y guía de downgrade para v2.0.0.
- [ ] **REL-03**: PC, Android físico, panel, luz, Spotify, Calendar, clima, timer, reminder, notificación y cámara completan smoke sobre el mismo commit de release.

## Future Requirements

### Capacidades diferidas

- **MULTI-01**: Más de un owner administra permisos y datos separados.
- **VOICE-03**: Wake word o escucha permanente con consentimiento y presupuesto demostrado.
- **MEDIA-03**: TTS en el panel o altavoces domésticos.
- **PLUGIN-01**: Marketplace o ejecución de código de terceros.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Exposición pública y port forwarding | La superficie doméstica remota debe permanecer en una VPN personal autenticada. |
| Reconocimiento de voz en ESP32 | Excede privacidad, RAM/Flash y consumo definidos para v2.0.0. |
| Multiusuario e invitados | v2.0.0 está diseñado para un único owner autenticado. |
| Automatizaciones que confirman por el owner | Violan la política A–D y el requisito de confirmación humana. |
| Video multicanal de alta tasa | El alcance de cámara se limita a disponibilidad, snapshot y una vista controlada. |
| Cloud obligatorio | Luces y funciones locales esenciales deben degradar sin dependencias no críticas. |

## Traceability

La trazabilidad de cada requisito v2.0.0 se define en `ROADMAP.md` y se actualiza al cerrar cada fase. Cada requisito pertenece a una sola fase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BASE-01 | Phase 1 — PR-00 | Complete |
| BASE-02 | Phase 1 — PR-00 | Complete |
| BASE-03 | Phase 1 — PR-00 | Complete |
| BASE-04 | Phase 1 — PR-00 | Pending |
| BASE-05 | Phase 1 — PR-00 | Pending |
| ARCH-01 | Phase 2 — PR-01 | Complete |
| ARCH-02 | Phase 2 — PR-01 | Complete |
| PROTO-01 | Phase 2 — PR-01 | Complete |
| PROTO-02 | Phase 2 — PR-01 | Complete |
| PROTO-03 | Phase 2 — PR-01 | Complete |
| IDENT-01 | Phase 3 — PR-02 | Automated complete; physical client pending |
| EVENT-01 | Phase 3 — PR-02 | Complete |
| EVENT-02 | Phase 3 — PR-02 | Complete |
| EVENT-03 | Phase 3 — PR-02 | Complete |
| SYNC-01 | Phase 4 — PR-03 | Automated complete; three physical clients pending |
| SYNC-02 | Phase 4 — PR-03 | Complete |
| SYNC-03 | Phase 4 — PR-03 | Complete |
| UI-01 | Phase 5 — PR-04 | Complete (automated) |
| UI-02 | Phase 5 — PR-04 | Automated configuration complete; physical performance and O-05 pending |
| UI-03 | Phase 5 — PR-04 | Complete |
| LIGHT-01 | Phase 6 — PR-05 | Automated complete; LEDVANCE and physical surfaces pending |
| LIGHT-02 | Phase 6 — PR-05 | Automated rollback/reconcile complete; physical p95 pending |
| LIGHT-03 | Phase 6 — PR-05 | Automated stress/failure/rollback complete; physical fault matrix pending |
| CONV-01 | Phase 7 — PR-06 | Automated complete; real Wyss and three physical surfaces pending |
| CONV-02 | Phase 7 — PR-06 | Complete (automated) |
| VOICE-01 | Phase 8 — PR-07 | Pending |
| VOICE-02 | Phase 8 — PR-07 | Pending |
| MEDIA-01 | Phase 9 — PR-08 | Pending |
| MEDIA-02 | Phase 9 — PR-08 | Pending |
| WEATHER-01 | Phase 10 — PR-09 | Pending |
| CAL-01 | Phase 11 — PR-10 | Pending |
| CAL-02 | Phase 11 — PR-10 | Pending |
| REM-01 | Phase 12 — PR-11 | Pending |
| REM-02 | Phase 12 — PR-11 | Pending |
| TIMER-01 | Phase 13 — PR-12 | Pending |
| TIMER-02 | Phase 13 — PR-12 | Pending |
| CAM-01 | Phase 14 — PR-13 | Pending |
| CAM-02 | Phase 14 — PR-13 | Pending |
| REMOTE-01 | Phase 15 — PR-14 | Pending |
| REMOTE-02 | Phase 15 — PR-14 | Pending |
| OTA-01 | Phase 16 — PR-15 | Pending |
| OTA-02 | Phase 16 — PR-15 | Pending |
| OBS-01 | Phase 17 — PR-16 | Pending |
| OBS-02 | Phase 17 — PR-16 | Pending |
| SEC-01 | Phase 18 — PR-17 | Pending |
| SEC-02 | Phase 18 — PR-17 | Pending |
| SOAK-01 | Phase 19 — PR-18 | Pending |
| SOAK-02 | Phase 19 — PR-18 | Pending |
| REL-01 | Phase 20 — PR-19 | Pending |
| REL-02 | Phase 20 — PR-19 | Pending |
| REL-03 | Phase 20 — PR-19 | Pending |

**Coverage:**
- v2.0.0 requirements: 51 total
- Mapped to phases: 51
- Unmapped: 0
- Duplicated mappings: 0

---
*Requirements defined: 2026-07-17*
*Last updated: 2026-07-17 after Phase 7 automated verification*
