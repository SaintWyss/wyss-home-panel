# Downgrade seguro de v2.0.0

## Gate previo

Yo no inicio el downgrade sin identificar el commit/artefacto v1 conocido, verificar su SHA-256 y
obtener dos backups legibles de configuración, identidad revocable y estado durable. No cambio
NVS, tabla de particiones, bootloader, eFuses, Secure Boot o Flash Encryption de forma implícita.

## Procedimiento

1. detener mutaciones y exportar timers activos, reminders y configuración no sensible;
2. registrar versiones, health, hashes y último cursor de eventos;
3. detener Home Edge v2, conservar su directorio de datos y activar el entorno v1 anterior mediante
   el symlink/servicio atómico;
4. verificar fixtures/protocolo v1 y usar sólo el artefacto firmware v1 firmado o con checksum ya
   aprobado;
5. escribir únicamente la partición de aplicación siguiendo el runbook físico aprobado; nunca
   borrar NVS como atajo;
6. arrancar, verificar display, touch, red, luz y autoridad Wyss, y reimportar sólo datos cuyo schema
   sea compatible;
7. si falla health, restaurar v2 sin migraciones adicionales y conservar toda evidencia.

## Aceptación

El downgrade sólo pasa si configuración/identidad verificables se preservan, los timers activos no
se duplican, v1 responde y los hashes coinciden. Este procedimiento está documentado pero aún no
ha sido ensayado físicamente para v2.0.0; por eso `SOAK-02` y `REL-02` siguen abiertos.
