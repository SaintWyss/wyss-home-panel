---
phase: 09-pr-08-spotify-premium
subsystem: media
tags: [spotify, wyss, projection, panel, oauth-boundary]
requires:
  - phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
    provides: proyección revisionada y entrega multicliente
provides:
  - Contrato Spotify sanitizado entre Wyss y Home Edge
  - Controles coherentes en PC, Android y panel sin OAuth fuera de Wyss
  - Feature flag, scopes mínimos y rollback aislado del shell
requirements-partial: [MEDIA-01, MEDIA-02]
completed-automated: 2026-07-17
---

# Phase 9: Spotify Premium Summary

**La integración, UI, fallos y rollback están automatizados; O-07 y la cuenta Premium real siguen pendientes.**

## Accomplishments

- Mantuvo a Wyss como única autoridad OAuth: Home Edge usa el token interno existente y nunca
  recibe access/refresh tokens de Spotify.
- Añadió `MediaPort`, dominio sanitizado, adapter fail-closed y `MediaService` serializado con
  revisión, idempotencia acotada y eventos `spotify.state.changed`.
- Validó sólo cuatro scopes necesarios para playback y biblioteca; el módulo no puede habilitarse
  si falta uno o aparece un scope sobrante.
- Proyectó reproducción, pista, artista, progreso, dispositivo, volumen, favorito y degradación a
  PC, Android y panel.
- Implementó play, pause, anterior, siguiente, volumen, favorito y transferencia de dispositivo
  mediante `capability.command` y capacidades mínimas por cliente.
- Cubrió 204, 401, 403, 404/dispositivo inactivo, 429/`Retry-After`, respuesta inválida, timeout de
  red, revisión obsoleta, replay y rollback por feature flag.
- Reemplazó el placeholder MEDIA del panel por controles táctiles de 48–58 px y snapshot visual
  determinista, sin endpoints ni credenciales del proveedor en firmware.

## Commits

1. **Proyección y controles Spotify a través de Wyss** - `75e9a9b`
2. **Controles Spotify en el panel** - `6efca4b`

## External Setup Pending

- Cerrar O-07 aprobando explícitamente los cuatro scopes registrados.
- Implementar/verificar OAuth y refresh dentro del repositorio/servicio autoritativo Wyss.
- Probar una cuenta Premium real en PC, Android y panel sobre el mismo commit.
- Ejercitar expiración real, revocación, rate limit real y dispositivo inactivo real.

