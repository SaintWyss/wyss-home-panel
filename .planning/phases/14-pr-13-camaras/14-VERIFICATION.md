---
phase: 14-pr-13-camaras
status: blocked-before-implementation-o03
verified_at: 2026-07-18T01:10:00Z
requirements: [CAM-01, CAM-02]
---

# Verification: Phase 14

La fase no entra en implementación porque su primer criterio es el gate O-03. No existe evidencia
de marca, modelo, protocolo, autenticación ni endpoints de una cámara real. Elegir ONVIF, RTSP o
una API propietaria por suposición produciría superficie y controles SSRF incorrectos.

## Preserved safe state

- `CameraPort` continúa siendo un contrato sin adapter real.
- La proyección conserva el shell `cameras` vacío y no retiene imágenes.
- No se agregaron credenciales, destinos LAN, listeners, dependencias ni defaults ocultos.
- Las demás capacidades y el firmware original de la pantalla continúan operativos.

## Evidence required to resume

Marca/modelo exactos, documentación o inspección del protocolo, forma de autenticación, endpoints
permitidos y un smoke LAN del hardware. Con eso se podrá diseñar allowlist SSRF, timeout,
redimensionado efímero, no-retención, health y revocación específicos y verificables.
