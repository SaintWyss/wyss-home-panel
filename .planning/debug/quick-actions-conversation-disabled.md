---
status: resolved
trigger: "Las acciones rápidas fallan."
created: 2026-07-18T03:25:00Z
updated: 2026-07-18T03:36:00Z
---

# Debug: acciones rápidas sin ejecución

## Causa raíz

Los tres botones enviaban `assistant.intent`, pero la conversación v2 estaba desactivada y la identidad del panel sólo tenía los permisos mínimos de proyección y luces. El bridge rechazaba el mensaje antes de ejecutar Tuya.

## Corrección

- `Modo noche` envía `set_brightness=20` a todas las luces disponibles.
- `Apagar todo` y `Estoy saliendo` envían `turn_off` a todas las luces disponibles.
- Los tres usan `home.command`, el mismo camino rápido, auditado y autorizado de los controles manuales.

## Verificación

- Regresión C++: confirma que no se envían intents y que sólo se apuntan luces disponibles.
- Suite C++/UI: 5/5.
- Suite Python: 215/215.
- Build PlatformIO: correcto.
- Flash app-only: hash verificado, NVS preservado.
- Prueba WebSocket/Tuya extremo a extremo: modo noche verificado y estado original restaurado.

## Seguimiento físico: potencia sin ACK

Durante la prueba táctil, color y brillo se verificaron, pero `turn_on` y `turn_off` quedaron como
`provider_unavailable`. El foco sí acepta esos writes de un único DP, pero a veces no devuelve un
ACK a `tinytuya.set_multiple_values()`.

La corrección no acepta éxito a ciegas: ante una respuesta silenciosa hace hasta tres lecturas
acotadas y sólo confirma si todos los DP pedidos coinciden exactamente. Una respuesta Tuya con
`Error`/`Err`, una lectura inválida o un estado distinto siguen fallando de forma segura.

- Regresión nueva: un foco fake aplica un DP sin ACK; encendido y apagado sólo pasan por lectura.
- Suite Python completa: 216/216.
- Ruff, formato y mypy: correctos.
- Prueba física directa: apagada → encendida → apagada, estado inicial restaurado.
