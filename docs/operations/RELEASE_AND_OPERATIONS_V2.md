# Operación y release de Wyss Home v2.0.0

## Unidades operativas

Yo despliego tres artefactos versionados:

1. firmware ESP32 `.bin` firmado;
2. servicio Home Edge Python instalado como systemd user;
3. integración compatible dentro de `SaintWyss/Wyss` y su Android APK.

Yo publico una matriz de compatibilidad y rechazo combinaciones incompatibles antes de actualizar.

## Instalación

Yo automatizo preflight de SO, red, espacio, puerto USB, modelo de placa, Flash/PSRAM, backup, certificados y servicios Wyss. Yo creo configuración desde plantilla, identidad por dispositivo y secretos con permisos mínimos. Yo nunca sobrescribo una configuración existente sin backup y diff.

Yo separo `install`, `doctor`, `provision`, `upgrade`, `rollback`, `backup` y `restore` como comandos idempotentes.

## Configuración

Yo mantengo TOML no sensible, `.env`/secret store sensible y schema versionado fail-fast. Yo agrego migraciones hacia adelante y rollback cuando sea seguro. Yo rechazo claves desconocidas y muestro errores accionables.

## Observabilidad

Yo expongo health por módulo: Wyss daemon, Home Edge, panel, luces, Spotify, Calendar, clima, push y cámaras. Yo publico métricas de latencia, reconexión, cola, errores, heap y versión. Yo correlaciono cada acción por `correlation_id` sin loguear contenido sensible.

El procedimiento concreto de lectura, alertas, aislamiento y rollback está en
[`OBSERVABILITY_RUNBOOK.md`](OBSERVABILITY_RUNBOOK.md).

Yo uso logs estructurados con niveles, rotación y redacción. Yo mantengo auditoría de negocio en Wyss y logs técnicos separados.

## Actualización de firmware

Yo implemento OTA A/B firmada después de validar carga USB. Yo verifico manifest, versión, board id, hash y firma antes de escribir. Yo marco imagen válida sólo después de boot, display, touch, red y handshake saludables. Si falla, yo vuelvo automáticamente a la partición anterior.

Yo mantengo USB/BOOT/RESET como recuperación y no activo eFuses hasta demostrar restore con dos copias verificadas del backup de fábrica.

## Actualización de servicios

Yo descargo una release identificada, verifico checksum/firma, creo venv nuevo, migro configuración/estado, ejecuto smoke y cambio symlink atómicamente. Si health falla, yo restauro versión anterior y estado compatible.

## Backups

Yo conservo:

- backup de fábrica de la Flash con SHA-256 ya documentado;
- identidad/CA y configuración cifradas;
- estado durable de timers y recordatorios;
- claves de recuperación y lista de dispositivos revocados;
- versión exacta de firmware, Edge y Wyss.

Yo no incluyo tokens OAuth ni credenciales sin cifrado. Yo pruebo restore trimestralmente o antes de cambios de seguridad.

## Runbooks

### Pantalla negra

Yo compruebo alimentación, backlight, logs seriales y watchdog. Yo intento RESET, luego BOOT+USB, y finalmente restauro firmware conocido. Yo no borro NVS antes de exportar diagnóstico.

### Panel desconectado

Yo verifico hora/CA, Wi-Fi, IP del Edge, revocación y versión de protocolo. Yo uso `doctor` y evito reprovisionar hasta identificar causa.

### Luz no responde

Yo verifico disponibilidad, IP y clave Tuya desde Edge. Yo bloqueo reintentos agresivos y mantengo estado unknown. Yo no marco éxito sin lectura real.

### OAuth vencido

Yo intento refresh una vez, marco el módulo desvinculado y solicito reautorización. Yo no reinicio otros módulos ni muestro token.

### Notificación no llega

Yo reviso permiso Android, canal, identidad, deduplicación y ack. Yo conservo alerta visible en la pantalla y estado pendiente.

### Compromiso o pérdida

Yo revoco el dispositivo, roto credenciales relacionadas, reviso auditoría y vuelvo a parear con identidad nueva.

## Release SemVer

Yo uso SemVer para el producto y versiono protocolo/config por separado. Yo genero prereleases `2.0.0-alpha.N`, `beta.N` y `rc.N`, pero yo no llamo MVP a ninguna etapa: cada fase es un incremento verificable hacia el alcance final ya fijado.

## Promoción

```text
feature branch → CI → simulator → hardware lab → alpha interna
→ integración real → beta diaria → RC congelada → soak 72 h
→ restore/rollback → v2.0.0
```

Yo firmo artefactos desde el commit aprobado, publico checksums/SBOM/notas y mantengo rollback disponible. Yo no promociono si existe un riesgo alto conocido sin aceptación explícita.

## Sostenibilidad

Yo reduzco brillo y FPS en idle, evito polling de servicios, uso eventos/cache, limito retención y mido tráfico/energía. Yo actualizo dependencias en ventanas controladas con Dependabot y contract tests, no por impulso.
