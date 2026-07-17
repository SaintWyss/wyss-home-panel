# Seguridad

## Modelo

Yo considero hostiles la Wi-Fi, los mensajes repetidos, un panel perdido y cualquier entrada textual. Yo considero la netbook confiable sólo mientras su usuario y su disco estén protegidos.

## Controles

- Yo exijo WSS con una CA privada y valido el certificado desde el ESP32.
- Yo genero un token aleatorio de 256 bits, guardo únicamente su SHA-256 en el puente y comparo en tiempo constante.
- Yo autorizo un identificador de panel y una lista cerrada de entidades.
- Yo limito el camino rápido a seis acciones de luces/escenas y a doce órdenes por segundo.
- Yo hago idempotentes los últimos 256 identificadores para no repetir acciones por reconexión.
- Yo limito cada trama a 8 KiB y cada intención v2 a 1.000 caracteres.
- Yo mantengo tokens de Wyss, Home Assistant y Tuya exclusivamente en variables de entorno de la netbook.
- Yo elimino el token temporal del disco después del aprovisionamiento confirmado.
- Yo ejecuto systemd con `NoNewPrivileges`, sistema de archivos protegido y `UMask=0077`.

## Riesgo físico

Yo reconozco que NVS sin cifrado permite extraer el token si alguien obtiene la placa y acceso de laboratorio. Para un despliegue fuera de un hogar controlado yo activo Secure Boot v2 y Flash Encryption en modo release después de verificar el respaldo de fábrica; yo trato esa operación de eFuse como irreversible y no la automatizo durante el desarrollo.

## Voz efímera

Yo sólo solicito micrófono durante un gesto visible y sostenido en PC o Android. El navegador corta
tracks al soltar, cancelar, perder foco o sufrir una interrupción. Home Edge acepta únicamente
formatos permitidos, limita el cuerpo a 4 MiB por defecto, aplica timeout y exige `pc.voice` o
`android.voice`. El buffer mutable se sobrescribe al terminar y no se registra, persiste ni proyecta.
La transcripción tampoco se envía sola: el owner la revisa y realiza un segundo gesto explícito.

El token de cliente vive sólo en `sessionStorage`, las respuestas usan `no-store` y la página aplica
CSP, `frame-ancestors 'none'` y una Permissions Policy limitada al propio origen. Mientras O-01 no
tenga una decisión del operador, no habilito un STT ni hago fallback silencioso a cloud.

## Política Wyss

Yo no dupliqué la autoridad del orquestador. Mi política del borde sólo permite acciones domésticas
de riesgo A. Yo envío toda intención abierta a Wyss y muestro el plan antes de confirmar riesgos
B/C. La primera respuesta válida gana mediante revisión y lock; TTL y `CONFIRMAR` se revisan antes
de llamar a Wyss. Wyss debe reevaluar política al confirmar y acreditarlo en la respuesta. Yo
rechazo riesgo D y también cualquier confirmación sin esa acreditación.
