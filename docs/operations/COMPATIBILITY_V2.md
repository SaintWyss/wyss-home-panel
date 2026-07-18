# Compatibilidad v2.0.0

| Componente | Compatible | Condición |
| --- | --- | --- |
| Panel | Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2, N16R8 | board/partición exactos; no asumir otras revisiones |
| Firmware | 2.0.0 | protocolo v2 preferido; handshake v1 conservado durante migración |
| Home Edge | bridge 2.0.0, Python 3.12+ | `uv.lock` exacto y configuración validada |
| LVGL | 8.4.0 | assets 800×480 y límites de RAM/Flash registrados |
| Wyss | contrato HTTP/WS documentado | autoridad única de policy, ejecución y auditoría |
| Luces | Tuya LAN o Home Assistant autorizados | entidad allowlisted; prueba física pendiente por dispositivo |
| Android/PC | cliente HTTPS/WS con identidad propia | pairing, revocación y permisos físicos pendientes |
| Spotify/Calendar | adapters deshabilitables | cuenta/scopes reales requieren aprobación O-07 |
| Cámara | no habilitada | requiere O-03: marca, modelo, protocolo, auth y endpoints |
| Remoto | LAN-only | requiere O-02 y Tailscale/WireGuard; no existe exposición pública |

No son compatibles ni están autorizados port forwarding, UPnP, una placa distinta asumida por
semejanza, secretos dentro del firmware, wake word permanente o una segunda autoridad mutable.

La combinación se considera soportada sólo después de que `doctor`, CI, health y el smoke físico
del commit exacto estén aprobados.
