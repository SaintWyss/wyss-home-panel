# Decisiones abiertas controladas

## Propósito

Yo registro aquí lo que todavía requiere hardware, benchmark o preferencia operativa. Yo no bloqueo documentación ya resuelta ni invento una decisión irreversible.

| Id | Decisión que yo debo cerrar | Momento límite | Evidencia que yo necesito |
| --- | --- | --- | --- |
| O-01 | Yo elegiré motor STT local para PC/Android. | Antes de PR-07 | Yo compararé precisión, latencia, CPU, privacidad y español argentino. |
| O-02 | Yo decidiré si habilito acceso fuera de LAN y qué VPN uso. | Antes de PR-14 | Yo confirmaré uso real, Android, ACL y recuperación. |
| O-03 | Yo identificaré marca/modelo/protocolo de cámara. | Antes de PR-13 | Yo inspeccionaré documentación, endpoints, auth y smoke LAN. |
| O-04 | Yo elegiré mecanismo de notificación Android. | Antes de PR-11 | Yo probaré Capacitor local notification, background y dedupe en teléfono real. |
| O-05 | Yo ajustaré brillo/FPS del modo dormido. | Antes de cerrar PR-04 | Yo mediré legibilidad, energía, temperatura y respuesta física. |
| O-06 | Yo decidiré cuándo activar Secure Boot/Flash Encryption. | Antes de v2.0.0 | Yo demostraré backup, rescue, OTA rollback y recuperación de claves. |
| O-07 | Yo definiré scopes OAuth definitivos. | PR-08/10 | Yo listaré pantallas/acciones y escogeré scopes mínimos verificados. |

Yo mantengo estas decisiones fuera del código hasta su ADR. Yo no permito que una decisión abierta se convierta en un default oculto.
