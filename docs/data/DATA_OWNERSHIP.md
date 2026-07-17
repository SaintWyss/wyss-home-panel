# Propiedad y ciclo de vida de datos

## Regla

Yo asigno una sola autoridad a cada dato. Yo permito caches y proyecciones, pero nunca dos fuentes de verdad mutables.

| Dato | Autoridad que yo elijo | Proyección/cache | Retención que yo defino |
| --- | --- | --- | --- |
| Identidad del owner y dispositivos | Wyss PC | Android/Panel guardan identidad pareada | Hasta revocación |
| Conversación completa | Wyss | Panel guarda sólo vista efímera | Configurable; audio crudo no se conserva por defecto |
| Plan, riesgo y pending | Wyss daemon | Panel/Android proyectan | TTL del pending + auditoría |
| Auditoría | `audit.db` de Wyss | Ninguna copia editable | Append-only según política de Wyss |
| Estado de luces | Dispositivo/adapter Home Edge | Wyss y Panel proyectan | Último estado + eventos acotados |
| Tokens Tuya/cámara | Home Edge secret store | Nunca en panel | Hasta rotación/revocación |
| OAuth Spotify/Google | Wyss secret store | Nunca en Edge/Panel | Hasta revocación; refresh rotado |
| Eventos Calendar | Google Calendar | Cache cifrado de próxima semana | TTL corto y purge explícito |
| Recordatorios | Wyss scheduler | Calendar/Android pueden proyectar | Hasta completar/eliminar |
| Temporizadores | Wyss scheduler | Panel/Android proyectan | Hasta completar + auditoría mínima |
| Pronóstico | Open-Meteo | Cache Home/Wyss | Último válido + 24 h |
| Cámara | Cámara/NVR | Panel recibe snapshot efímero | Sin grabación en Wyss Home por defecto |
| Preferencias UI | Wyss owner memory/config | Panel cachea tema/brillo | Hasta cambio/reset |
| Métricas | Cada proceso produce; observabilidad agrega | Series acotadas | 30 días por defecto |

## Clasificación

Yo clasifico como secretos los refresh tokens, claves Tuya, credenciales de cámara, claves privadas TLS y tokens de pairing. Yo clasifico como sensibles la voz, conversación, agenda, nombres de dispositivos, presencia, snapshots y patrones de uso.

Yo nunca incluyo secretos en Git, firmware, backup publicado, URL persistente, telemetry, crash dump ni auditoría. Yo redacto encabezados y payloads antes de loguear.

## Privacidad de voz

Yo capturo audio únicamente mientras mantengo presionado el botón. Yo transcribo en PC cuando sea posible. Si uso un proveedor externo, yo minimizo el audio/contexto y hago visible el proveedor activo. Yo elimino el buffer después de transcribir y no lo agrego a memoria automáticamente.

## Exportación y eliminación

Yo reutilizo las capacidades de export/delete de Wyss cuando existan. Yo agrego a Home Edge comandos administrativos separados para listar identidad, borrar caches, revocar el panel y resetear NVS. Yo exijo confirmación fuerte antes de borrar credenciales o desvincular el hogar.
