---
phase: 08-pr-07-push-to-talk-pc-y-android
subsystem: voice
tags: [push-to-talk, privacy, pc, android, accessibility]
requires:
  - phase: 07-pr-06-conversacion-visual-y-confirmaciones
    provides: funnel conversacional compartido y autoridad única de Wyss
provides:
  - Cliente PTT responsive para PC y Android con revisión y envío explícito
  - Audio efímero autenticado fuera del canal de control
  - Feature flag y adapter fail-closed mientras O-01 permanece abierta
requirements-partial: [VOICE-01, VOICE-02]
completed-automated: 2026-07-17
---

# Phase 8: Push-to-talk Summary

**La captura, privacidad, UI y fallos están automatizados; O-01 y los micrófonos reales siguen pendientes.**

## Accomplishments

- Sirvió un cliente HTML/CSS/JS sin dependencias que funciona en PC y Android modernos sobre HTTPS.
- Capturó únicamente entre press y release, con cancelación por pointer, teclado, pérdida de foco o
  interrupción del track.
- Separó transcripción de envío: el owner puede editar, borrar o cancelar y sólo un segundo gesto
  crea `assistant.intent`.
- Reutilizó el parser v2 y `ConversationService`, sin crear un planificador o ejecutor paralelo.
- Exigió capacidades `pc.voice`/`android.voice`, límites de formato/tamaño/timeout y `no-store`.
- Sobrescribió el buffer mutable en `finally` y evitó audio en eventos, proyecciones y respuestas.
- Conservó el editor de texto cuando `voice_enabled = false`.
- Aplicó CSP, sesión de token acotada a la pestaña, targets de 44 px, foco visible, live region y
  reduced motion.

## Commits

1. **Cliente y ciclo privado de voz** - `5eab660`
2. **Matriz de privacidad y fallos** - `05cb850`

## External and Physical Setup Pending

- Cerrar O-01 comparando y eligiendo el motor STT local para español argentino.
- Conectar ese adapter real sin habilitar fallback implícito a cloud.
- Probar permisos, mantener/soltar, editar, cancelar, silencio, ruido e interrupción en PC y Android
  físicos sobre el mismo commit.
