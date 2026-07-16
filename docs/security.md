# Seguridad

## Modelo

Yo considero hostiles la Wi-Fi, los mensajes repetidos, un panel perdido y cualquier entrada textual. Yo considero la netbook confiable sólo mientras su usuario y su disco estén protegidos.

## Controles

- Yo exijo WSS con una CA privada y valido el certificado desde el ESP32.
- Yo genero un token aleatorio de 256 bits, guardo únicamente su SHA-256 en el puente y comparo en tiempo constante.
- Yo autorizo un identificador de panel y una lista cerrada de entidades.
- Yo limito el camino rápido a cinco acciones de luces/escenas y a doce órdenes por segundo.
- Yo hago idempotentes los últimos 256 identificadores para no repetir acciones por reconexión.
- Yo limito cada trama a 8 KiB y cada intención a 500 caracteres.
- Yo mantengo tokens de Wyss, Home Assistant y Tuya exclusivamente en variables de entorno de la netbook.
- Yo elimino el token temporal del disco después del aprovisionamiento confirmado.
- Yo ejecuto systemd con `NoNewPrivileges`, sistema de archivos protegido y `UMask=0077`.

## Riesgo físico

Yo reconozco que NVS sin cifrado permite extraer el token si alguien obtiene la placa y acceso de laboratorio. Para un despliegue fuera de un hogar controlado yo activo Secure Boot v2 y Flash Encryption en modo release después de verificar el respaldo de fábrica; yo trato esa operación de eFuse como irreversible y no la automatizo durante el desarrollo.

## Política Wyss

Yo no dupliqué la autoridad del orquestador. Mi política del borde sólo permite acciones domésticas de riesgo A. Yo envío toda intención abierta a Wyss y muestro el plan antes de confirmar riesgos B/C. Yo rechazo riesgo D.

