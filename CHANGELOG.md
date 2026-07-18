# Changelog

Todos los cambios relevantes siguen SemVer y este proyecto conserva compatibilidad v1 durante la
ventana de migración de v2.0.0.

## [2.0.0] — pendiente de promoción

### Agregado

- contratos v2 compartidos Python/C++, identidad por cliente, eventos SQLite y sincronización por
  snapshot/deltas;
- shell Wyss Core para panel, modo manual/dormido, conversación visual y confirmaciones;
- luces revisionadas con idempotencia durable, Spotify, clima, Calendar, reminders y timers detrás
  de ports y gates explícitos;
- OTA firmada/health lógico, observabilidad acotada, SBOM CycloneDX, dependency/secret scan y suite
  adversarial;
- soak acelerado reproducible de 1.000 reconexiones, 500 cambios y 100 timers.

### Seguridad

- allowlists de entidades/orígenes, fail-closed en protocolo y providers, scopes mínimos y
  redacción de secretos;
- dependencias Python bloqueadas y dependencias Git de firmware fijadas por commit;
- cámara y acceso remoto permanecen deshabilitados hasta resolver sus gates.

### Compatibilidad

- protocolo v1 y fixtures dorados permanecen operativos durante la migración;
- v2.0.0 requiere Python 3.12+, Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2 N16R8 y LVGL 8.4.0;
- ver `docs/operations/COMPATIBILITY_V2.md` y `docs/operations/DOWNGRADE_V2.md`.

### Pendiente antes de publicar

- protección remota de `main`, soak físico de 72 h, matriz E2E con hardware/cuentas, firma con la
  clave real y ensayos físicos de upgrade/backup/restore/downgrade.

## [1.0.0] — baseline

- panel táctil LVGL, bridge TLS local, luces Tuya/Home Assistant, provisioning USB y rollback
  optimista verificado.
