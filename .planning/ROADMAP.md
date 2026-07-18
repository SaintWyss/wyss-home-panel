# Roadmap: Wyss Home Panel v2.0.0

## Overview

Este milestone lleva el baseline v1 hasta un sistema doméstico v2.0.0 coherente y recuperable mediante veinte incrementos verticales, uno por PR del plan maestro. El orden congela primero evidencia y contratos; después habilita identidad, sincronización y capacidades; y finalmente cierra operación, seguridad, soak y release. Cada fase conserva la autoridad única de Wyss, compatibilidad v1 y rollback explícito. La evidencia física o de proveedores externos debe corresponder al commit probado; si falta, la fase queda bloqueada y no se sustituye por simulación.

## Phases

- [ ] **Phase 1: PR-00 — Baseline reproducible y protección** - Congelar build, pruebas, fixtures, métricas, backup y gates antes de cambiar el runtime.
- [x] **Phase 2: PR-01 — Contratos y arquitectura v2** - Definir ports, envelope v2 y límites arquitectónicos sin adapters reales.
- [ ] **Phase 3: PR-02 — Identidad, pairing y event backbone** - Conectar clientes y Edge con identidad revocable y eventos reanudables.
- [ ] **Phase 4: PR-03 — Projection Store y sincronización multicliente** - Hacer converger PC, Android y panel sobre proyecciones revisionadas.
- [ ] **Phase 5: PR-04 — Shell visual Wyss Core y modo dormido** - Entregar la experiencia visual final, accesible y dentro de presupuesto físico.
- [ ] **Phase 6: PR-05 — Luces completas y migración del baseline** - Operar varias luces desde un único port con degradación segura.
- [ ] **Phase 7: PR-06 — Conversación visual y confirmaciones** - Proyectar el ciclo de Wyss y preservar la política A–D sin bypass.
- [ ] **Phase 8: PR-07 — Push-to-talk PC y Android** - Incorporar voz deliberada, editable y privada como entrada opcional.
- [ ] **Phase 9: PR-08 — Spotify Premium** - Controlar reproducción real desde cualquier cliente sin filtrar tokens.
- [ ] **Phase 10: PR-09 — Clima semanal** - Mostrar clima actual y siete días con cache y antigüedad explícitos.
- [ ] **Phase 11: PR-10 — Google Calendar** - Consultar y administrar agenda mediante Wyss, scopes mínimos y confirmación.
- [ ] **Phase 12: PR-11 — Recordatorios y notificaciones Android** - Mantener recordatorios durables y entregar una notificación recuperable.
- [ ] **Phase 13: PR-12 — Temporizadores durables** - Operar timers persistentes con finalización exactamente una vez.
- [ ] **Phase 14: PR-13 — Cámaras** - Exponer disponibilidad y snapshots efímeros de hardware identificado y aislado.
- [ ] **Phase 15: PR-14 — Acceso remoto privado y operación móvil** - Permitir operación remota sólo por VPN privada autenticada.
- [ ] **Phase 16: PR-15 — OTA, provisioning y recovery de producción** - Actualizar y recuperar la placa sin perder configuración ni tocar eFuses.
- [ ] **Phase 17: PR-16 — Observabilidad, rendimiento y sostenibilidad** - Medir presupuestos finales y aislar fallos sin exponer secretos.
- [ ] **Phase 18: PR-17 — Hardening y suite adversarial** - Cerrar la superficie doméstica y sus riesgos altos antes de release.
- [ ] **Phase 19: PR-18 — Beta diaria y soak** - Probar el producto completo bajo carga, reconexión, fallos y migraciones reales.
- [ ] **Phase 20: PR-19 — Release v2.0.0 final** - Publicar exactamente el commit trazado, firmado y validado en todas las superficies.

## Phase Details

### Phase 1: PR-00 — Baseline reproducible y protección
**Goal**: El operador puede reproducir y diagnosticar el baseline protegido antes de evolucionar el runtime.
**Depends on**: Nothing (first phase)
**Requirements**: BASE-01, BASE-02, BASE-03, BASE-04, BASE-05
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** Desde un checkout limpio, el operador reproduce el build de firmware, los tests de Home Edge y los fixtures v1 con versiones registradas.
  2. **[Automatizada]** `doctor` informa toolchain, dependencias y configuración insegura con redacción de secretos, y CI bloquea dominio, bridge, firmware, secret scan y documentación esencial cuando fallan.
  3. **[Física]** El commit probado tiene evidencia fechada del backup de fábrica y mediciones comparables de LVGL/touch, Tuya, RAM y Flash; sin placa y luz reales este criterio permanece bloqueado.
  4. **[Física]** El smoke de la luz real confirma que el baseline continúa operativo sin alterar credenciales, NVS ni firmware estable.
**Plans**: 3/4; CI/protección completa, evidencia física pendiente

### Phase 2: PR-01 — Contratos y arquitectura v2
**Goal**: Los runtimes comparten contratos v2 cerrados y ports estables sin comprometer el camino v1.
**Depends on**: Phase 1
**Requirements**: ARCH-01, ARCH-02, PROTO-01, PROTO-02, PROTO-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** Python y C++ aceptan el mismo envelope v2 válido y rechazan versiones, campos, tamaños, duplicados y mensajes incompatibles.
  2. **[Automatizada]** Los fixtures dorados compartidos cubren replay, revisión, snapshot, delta y errores con el mismo resultado en ambos lenguajes.
  3. **[Automatizada]** Cada capacidad v2 tiene un port pequeño antes de cualquier adapter real y los checks de imports bloquean dependencias que crucen límites hexagonales.
  4. **[Automatizada]** La suite v1 sigue pasando y el runtime v1 puede arrancar sin activar consumidores v2.
**Plans**: 3

### Phase 3: PR-02 — Identidad, pairing y event backbone
**Goal**: Cada cliente se autentica de forma independiente y recupera eventos sin repetir acciones ni eludir a Wyss.
**Depends on**: Phase 2
**Requirements**: IDENT-01, EVENT-01, EVENT-02, EVENT-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** El operador puede emparejar, rotar y revocar una identidad por dispositivo, y un cliente real revocado es rechazado inmediatamente.
  2. **[Automatizada]** Tras desconexión, un cliente reanuda con heartbeat, cursor, snapshot y deltas ordenados sin reejecutar mensajes ya aceptados.
  3. **[Automatizada]** Rate limit, idempotencia, revisión y correlación son observables en todos los mensajes v2, y el Edge sólo llega a Wyss mediante su funnel público.
  4. **[Automatizada]** Desactivar el feature flag v2 restaura el listener v1 sin perder configuración, identidad autorizada ni autoridad.
**Plans**: 3

### Phase 4: PR-03 — Projection Store y sincronización multicliente
**Goal**: PC, Android y panel observan una proyección coherente después de una acción originada en cualquiera de ellos.
**Depends on**: Phase 3
**Requirements**: SYNC-01, SYNC-02, SYNC-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** Un cambio iniciado en PC, Android o panel converge en las tres superficies sin duplicación ni polling agresivo; el cierre exige los tres clientes reales sobre el mismo commit.
  2. **[Automatizada]** Cada agregado aplica revisión monotónica, reducers deterministas y recuperación por snapshot más deltas aun ante mensajes retrasados o repetidos.
  3. **[Automatizada]** Los límites de cache se hacen cumplir y ningún cliente puede escribir estado como autoridad paralela fuera del funnel de Wyss.
  4. **[Automatizada]** El fallback a snapshots periódicos puede activarse sin perder la autoridad ni corromper revisiones persistidas.
**Plans**: 3
**UI hint**: yes

### Phase 5: PR-04 — Shell visual Wyss Core y modo dormido
**Goal**: El owner puede navegar la experiencia Wyss Core final en modo activo, manual, conversacional y dormido.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** El simulador y las pruebas visuales cubren navegación, textos largos, offline, confirmaciones, contraste y cambios visuales intencionales.
  2. **[Física]** En la placa real, tacto→paint es ≤50 ms p95, la UI activa sostiene ≥30 FPS, el reposo 5–10 FPS y los objetivos táctiles miden ≥44 px; sin medición ligada al commit no se cierra.
  3. **[Física]** RAM, Flash, brillo, energía, temperatura y legibilidad permanecen dentro de presupuestos registrados en el panel exacto.
  4. **[Gate O-05 — física]** Antes de cerrar PR-04, el operador decide brillo/FPS de modo dormido con mediciones de legibilidad, energía, temperatura y respuesta; el resultado queda en una ADR.
**Plans**: 2
**UI hint**: yes

### Phase 6: PR-05 — Luces completas y migración del baseline
**Goal**: El owner controla varias luces desde cualquier superficie y conserva control local esencial durante fallos.
**Depends on**: Phase 4
**Requirements**: LIGHT-01, LIGHT-02, LIGHT-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** PC, Android y panel controlan encendido, brillo, color, escenas y disponibilidad de varias luces mediante un único `LightPort`; el cierre requiere LEDVANCE/Tuya real.
  2. **[Física]** El feedback optimista revierte al fallar y reconcilia estado LAN en ≤150 ms p95 bajo condiciones saludables, medido sobre el commit exacto.
  3. **[Automatizada + física]** Tras 500 cambios, caída y recuperación de Wi-Fi, clave inválida o foco offline no hay carreras ni estado fantasma, y las luces manuales autorizadas siguen disponibles cuando fallan servicios no críticos.
  4. **[Automatizada]** Volver al adapter/binario estable conserva credenciales y NVS y deja el audit trail consistente.
**Plans**: 4
**UI hint**: yes

### Phase 7: PR-06 — Conversación visual y confirmaciones
**Goal**: El owner observa un ciclo conversacional coherente y ninguna acción supera la política A–D sin la confirmación requerida.
**Depends on**: Phase 4
**Requirements**: CONV-01, CONV-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** Texto enviado desde PC, Android o panel comparte sesión y proyecta `idle`, `thinking`, confirmación, ejecución, verificación y fallo en las tres superficies.
  2. **[Automatizada]** Acciones A, B, C y D prueban TTL, primera confirmación válida, carrera concurrente y reevaluación de política; B/C no ejecutan sin confirmación válida y D no admite bypass.
  3. **[Automatizada]** Desactivar streaming conserva respuestas completas, historial autoritativo en Wyss y la misma política de confirmación.
**Plans**: 3
**UI hint**: yes

### Phase 8: PR-07 — Push-to-talk PC y Android
**Goal**: El owner puede dictar de forma deliberada, revisar el texto y enviarlo sin retener audio crudo.
**Depends on**: Phase 7
**Requirements**: VOICE-01, VOICE-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-01 — externa]** Antes de PR-07, el operador elige el motor STT local tras comparar precisión, latencia, CPU, privacidad y español argentino, y registra la decisión en una ADR.
  2. **[Física]** En PC y Android físico, el audio sólo se captura mientras el control visible está pulsado; el owner puede editar, cancelar y enviar explícitamente la transcripción.
  3. **[Automatizada + física]** Permiso negado, silencio, ruido, interrupción y proveedor caído terminan en estados recuperables sin envío implícito.
  4. **[Automatizada]** El audio crudo se elimina por defecto, no aparece en logs o proyecciones y voz puede desactivarse conservando texto como camino principal.
**Plans**: 3
**UI hint**: yes

### Phase 9: PR-08 — Spotify Premium
**Goal**: El owner observa y controla Spotify Premium desde cualquier superficie sin exponer credenciales OAuth.
**Depends on**: Phase 4
**Requirements**: MEDIA-01, MEDIA-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-07 — externa]** Antes de habilitar Spotify, el operador aprueba scopes mínimos para las acciones reales y registra la decisión; ningún scope sobrante se acepta por defecto.
  2. **[Externa + física]** Con una cuenta Premium real, PC, Android y panel ven playback/dispositivo coherente y controlan play, pausa, pista, volumen y favoritos.
  3. **[Automatizada + externa]** Expiración, 204, 401, 429 y dispositivo inactivo producen recuperación o error explícito sin perder coherencia multicliente.
  4. **[Automatizada]** Tokens nunca alcanzan clientes, fixtures o logs; revocar OAuth u ocultar el módulo no afecta el shell.
**Plans**: 3
**UI hint**: yes

### Phase 10: PR-09 — Clima semanal
**Goal**: El owner ve clima actual y siete días de Resistencia con procedencia temporal y degradación comprensibles.
**Depends on**: Phase 4
**Requirements**: WEATHER-01
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + externa]** La card muestra condición actual y siete días para Resistencia, Chaco, con timezone correcto, códigos normalizados y antigüedad visible usando respuestas reales del proveedor.
  2. **[Automatizada]** Offline, cache vencido, valores faltantes y error del proveedor muestran último dato o ausencia explícita sin inventar frescura.
  3. **[Física]** El panel real presenta la card en modos idle y manual y mantiene el tráfico dentro del presupuesto medido para el commit.
**Plans**: 2
**UI hint**: yes

### Phase 11: PR-10 — Google Calendar
**Goal**: El owner consulta y modifica su agenda mediante Wyss con sincronización y política correctas.
**Depends on**: Phase 7
**Requirements**: CAL-01, CAL-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-07 — externa]** Antes de habilitar Calendar, el operador aprueba scopes separados mínimos para lectura y escritura y registra la decisión.
  2. **[Externa + física]** Con una cuenta real, el owner ve agenda diaria/semanal y crea, edita o elimina un evento desde los clientes previstos, pasando por plan, policy y confirmación.
  3. **[Automatizada + externa]** Sync incremental, paginación, recurrencia, all-day, timezone, token vencido e invalidación de cursor convergen sin duplicar ni perder eventos.
  4. **[Automatizada]** Revocar write scope conserva lectura/cache explícito y ningún token aparece en clientes o logs.
**Plans**: 2/2 automated; O-07 and account physical pending
**UI hint**: yes

### Phase 12: PR-11 — Recordatorios y notificaciones Android
**Goal**: El owner conserva recordatorios durables y recibe exactamente una notificación Android recuperable.
**Depends on**: Phase 11
**Requirements**: REM-01, REM-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-04 — física]** Antes de PR-11, el operador elige el mecanismo de notificación tras probar background, permisos, deduplicación y deep link en teléfono real, y lo registra en una ADR.
  2. **[Automatizada]** Recordatorios únicos o recurrentes sobreviven reinicio y permiten completar o posponer sin perder su próxima ocurrencia.
  3. **[Física]** Tras pérdida y recuperación de conectividad, Android físico entrega una sola notificación y su deep link abre el recordatorio correcto; permisos negados se muestran sin borrar el dato.
  4. **[Automatizada]** Desactivar push conserva el recordatorio autoritativo en Wyss y permite reanudar entrega sin duplicación.
**Plans**: 2/2 automated; O-04 and Android physical pending
**UI hint**: yes

### Phase 13: PR-12 — Temporizadores durables
**Goal**: El owner opera timers desde cualquier superficie y cada vencimiento se publica exactamente una vez.
**Depends on**: Phase 12
**Requirements**: TIMER-01, TIMER-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** PC, Android y panel crean, pausan, reanudan y cancelan timers y presets con el mismo estado revisionado.
  2. **[Automatizada]** Reinicios de procesos/panel y ajustes de reloj recuperan el deadline correcto sin timers perdidos o fantasmas.
  3. **[Automatizada + física]** Cien timers emiten exactamente un `timer.completed` cada uno y Android físico recibe una sola notificación por vencimiento.
  4. **[Automatizada]** Exportar, volver al scheduler anterior y reimportar timers activos preserva identidad, deadline y estado.
**Plans**: 2/2 automated; Wyss/Android physical pending
**UI hint**: yes

### Phase 14: PR-13 — Cámaras
**Goal**: El owner consulta una cámara identificada mediante snapshots efímeros sin ampliar la superficie doméstica.
**Depends on**: Phase 4
**Requirements**: CAM-01, CAM-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-03 — física/externa]** Antes de PR-13, el operador identifica marca, modelo, protocolo, autenticación y endpoints con documentación o inspección del hardware real y registra la decisión.
  2. **[Física]** Con la cámara real, el owner ve disponibilidad y un snapshot redimensionado efímero; no queda retención ni credencial en firmware, proyecciones o logs.
  3. **[Automatizada + física]** Credencial inválida, offline, timeout, SSRF y destino no autorizado fallan cerrados y no permiten pivote de red.
  4. **[Automatizada]** Revocar credencial y deshabilitar el adapter conserva el shell y las demás capacidades operativas.
**Plans**: 0/TBD; blocked before implementation by O-03 hardware identification
**UI hint**: yes

### Phase 15: PR-14 — Acceso remoto privado y operación móvil
**Goal**: El owner opera fuera de la LAN únicamente mediante una red privada revocable por dispositivo.
**Depends on**: Phase 3
**Requirements**: REMOTE-01, REMOTE-02
**Success Criteria** (what must be TRUE):
  1. **[Gate O-02 — externa]** Antes de PR-14, el operador decide si habilita acceso remoto y elige Tailscale o WireGuard tras evaluar Android, ACL, DNS y recuperación; la elección queda en una ADR.
  2. **[Física/externa]** Desde datos móviles y con VPN activa, un dispositivo autorizado opera el sistema mediante ACL y DNS privados; un dispositivo revocado es rechazado.
  3. **[Física/externa]** Pérdida de VPN y rollback vuelven a LAN-only, y un scan externo confirma que no hay listeners públicos ni port forwarding.
  4. **[Automatizada]** La automatización de configuración es idempotente y no persiste claves privadas en el repositorio o logs.
**Plans**: 0/TBD; blocked before implementation by O-02 operator decision

### Phase 16: PR-15 — OTA, provisioning y recovery de producción
**Goal**: El operador actualiza, restaura y rescata la placa sin perder configuración ni realizar cambios irreversibles.
**Depends on**: Phase 5
**Requirements**: OTA-01, OTA-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** Manifest, checksum y firma rechazan imagen corrupta o no autorizada antes de promoverla como saludable.
  2. **[Física]** En la placa real, imagen válida, firma inválida, corrupción y corte de energía ejercitan A/B, health boot y rollback hasta una imagen conocida.
  3. **[Automatizada + física]** Provisioning, migración, backup, restore y rescate USB son repetibles e idempotentes y conservan configuración verificable.
  4. **[Gate constitucional P8 — operador]** eFuses, Secure Boot y Flash Encryption permanecen sin tocar salvo autorización explícita separada; la fase prueba recuperación sin asumir esa activación.
**Plans**: 2/3 automated; A/B/provisioning physical evidence pending

### Phase 17: PR-16 — Observabilidad, rendimiento y sostenibilidad
**Goal**: El operador puede demostrar presupuestos de rendimiento y aislar degradaciones sin filtrar datos sensibles.
**Depends on**: Phase 6
**Requirements**: OBS-01, OBS-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** Un reporte ligado al commit muestra p50/p95/p99 de latencia, arranque, FPS, heap, tráfico y energía; métricas de hardware se declaran bloqueadas hasta medirse físicamente.
  2. **[Automatizada]** Métricas y traces correlacionan un flujo entre clientes, Edge y Wyss sin registrar secretos, audio, OAuth o credenciales domésticas.
  3. **[Automatizada]** `doctor`, backpressure, caches acotados y alertas detectan y aíslan fallos inducidos sin agotar memoria ni tumbar funciones esenciales.
  4. **[Automatizada]** Los runbooks reproducen diagnóstico y rollback de módulos no críticos manteniendo health básico.
**Plans**: 2/2 automated; hardware energy/FPS/startup metrics pending

### Phase 18: PR-17 — Hardening y suite adversarial
**Goal**: Las fronteras domésticas conocidas resisten abuso y ningún riesgo crítico o alto queda abierto.
**Depends on**: Phases 8, 9, 11, 14, 15, 16
**Requirements**: SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** La suite adversarial cubre parser/fuzz, replay, downgrade, SSRF, injection, carreras, revocación y scopes y falla cerrada en cada frontera.
  2. **[Automatizada]** Dependency scan, SBOM y secret scan son reproducibles y bloquean componentes o material sensible no permitido.
  3. **[Automatizada + revisión humana]** No queda ningún hallazgo crítico o alto abierto; cada riesgo restante registra owner, impacto, mitigación y fecha.
  4. **[Automatizada]** Revertir una funcionalidad problemática conserva la segunda muralla de política, identidad, allowlists y controles esenciales.
**Plans**: 2/2 automated; protección remota cerrada, superficies externas gated

### Phase 19: PR-18 — Beta diaria y soak
**Goal**: El sistema completo demuestra estabilidad, recuperación y migración sobre la matriz E2E real.
**Depends on**: Phases 17, 18
**Requirements**: SOAK-01, SOAK-02
**Success Criteria** (what must be TRUE):
  1. **[Automatizada + física]** Un soak de 72 horas sobre el commit exacto completa 1.000 reconexiones, 500 cambios de brillo y 100 timers sin crash, watchdog, estado fantasma ni duplicación.
  2. **[Automatizada + física]** Fault injection en red, proveedores y procesos conserva funciones esenciales o muestra degradación explícita y recuperable.
  3. **[Física]** Upgrade desde v1, backup/restore y rollback en la matriz real preservan datos, configuración e identidades verificadas.
  4. **[Física/externa]** Toda dependencia de hardware o proveedor ausente queda como bloqueo de fase; simuladores sólo aportan evidencia complementaria.
**Plans**: 2/2 automated; 72 h/physical migration matrix pending

### Phase 20: PR-19 — Release v2.0.0 final
**Goal**: El operador publica un artefacto v2.0.0 trazable y puede volver de forma segura a una versión conocida.
**Depends on**: Phase 19
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. **[Automatizada]** Los 51 requisitos enlazan evidencia de test y, donde corresponde, evidencia física del mismo commit; CI queda verde y la trazabilidad alcanza 100 %.
  2. **[Automatizada + revisión humana]** Artefactos versionados, checksums, SBOM, firmas, changelog, compatibilidad, límites y guía de downgrade coinciden con el tag v2.0.0.
  3. **[Física/externa]** PC, Android físico, panel, luz, Spotify, Calendar, clima, timer, reminder, notificación y cámara completan smoke sobre el mismo commit; cualquier dependencia ausente bloquea el release.
  4. **[Gate O-06 — operador/física]** Antes de v2.0.0, el operador decide cuándo activar Secure Boot/Flash Encryption sólo después de demostrar backup, rescue, OTA rollback y recuperación de claves; activarlos requiere autorización explícita separada.
  5. **[Física]** El downgrade ensayado recupera una versión v1/RC conocida con datos y configuración preservados.
**Plans**: 2/3 automated preparation; signature/publication/physical gates pending

## Progress

**Execution Order:** Phases execute in numeric order from 1 (PR-00) through 20 (PR-19). Dependencies above identify the minimum technical prerequisites; numeric order is the integration order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PR-00 — Baseline reproducible y protección | 3/4 | CI/protección complete; physical evidence pending | - |
| 2. PR-01 — Contratos y arquitectura v2 | 3/3 | Complete | 2026-07-17 |
| 3. PR-02 — Identidad, pairing y event backbone | 3/3 | Automated complete; physical pending | - |
| 4. PR-03 — Projection Store y sincronización multicliente | 3/3 | Automated complete; physical pending | - |
| 5. PR-04 — Shell visual Wyss Core y modo dormido | 2/2 | Automated complete; physical pending | - |
| 6. PR-05 — Luces completas y migración del baseline | 4/4 | Automated complete; physical pending | - |
| 7. PR-06 — Conversación visual y confirmaciones | 3/3 | Automated complete; physical E2E pending | - |
| 8. PR-07 — Push-to-talk PC y Android | 3/3 | Automated complete; O-01 and physical pending | - |
| 9. PR-08 — Spotify Premium | 3/3 | Automated + panel boot complete; O-07/account pending | - |
| 10. PR-09 — Clima semanal | 2/2 | Automated + provider + panel boot complete; physical projection pending | - |
| 11. PR-10 — Google Calendar | 2/2 | Automated + panel boot complete; O-07/account pending | - |
| 12. PR-11 — Recordatorios y notificaciones Android | 2/2 | Automated complete; O-04/physical pending | - |
| 13. PR-12 — Temporizadores durables | 2/2 | Automated complete; provider/physical pending | - |
| 14. PR-13 — Cámaras | gate | Blocked by O-03 hardware/protocol identification | - |
| 15. PR-14 — Acceso remoto privado y operación móvil | gate | Blocked by O-02 operator decision | - |
| 16. PR-15 — OTA, provisioning y recovery de producción | 2/2 | Automated signature/health complete; physical recovery pending | - |
| 17. PR-16 — Observabilidad, rendimiento y sostenibilidad | 2/2 | Automated complete; physical budgets pending | - |
| 18. PR-17 — Hardening y suite adversarial | 2/2 | Automated + remote protection complete; external surfaces gated | - |
| 19. PR-18 — Beta diaria y soak | 2/2 | Automated accelerated complete; 72 h/physical migration pending | - |
| 20. PR-19 — Release v2.0.0 final | 2/3 | Release candidate tooling/docs ready; publication blocked | - |
