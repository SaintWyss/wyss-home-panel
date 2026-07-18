---
phase: 10-pr-09-clima-semanal
subsystem: weather
tags: [open-meteo, weather, projection, lvgl, offline-cache]
requires:
  - phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
    provides: proyeccion revisionada y entrega multicliente
provides:
  - Pronostico actual y de siete dias para Resistencia con timezone fijo
  - Cache durable con frescura, vencimiento y fallos explicitos
  - Card LVGL manual y dormida con regresion visual
requirements-partial: [WEATHER-01]
completed-automated: 2026-07-18
---

# Phase 10: Clima semanal Summary

**Backend, proveedor real, degradacion, UI y arranque del panel estan verificados; falta proyectar
el dato real en el panel fisico provisionado para cerrar WEATHER-01.**

## Accomplishments

- Integro Open-Meteo mediante un port estricto con coordenadas fijas de Resistencia, timezone
  `America/Argentina/Cordoba`, codigos WMO normalizados y exactamente siete dias.
- Agrego cache SQLite privada y durable; distingue dato fresco, cache vieja, cache vencida,
  proveedor caido, respuesta invalida y ausencia de valores sin inventar frescura.
- Refresca el pronostico cada 30 minutos mientras existe al menos un cliente conectado, sin
  requerir que el panel se reconecte ni multiplicar llamadas por cantidad de clientes.
- Proyecta el mismo estado sanitizado a PC, Android y panel; la feature flag apagada no crea
  cache ni altera el shell.
- Reemplazo el placeholder de Inicio por una card actual/semanal y muestra antiguedad tambien en
  modo dormido. Los estados fresco, cache y sin proveedor tienen texto y color diferenciados.
- Agrego regresion visual determinista de 11 escenas, incluida cache de tres horas, y prueba que
  una cache corrupta degrada sin cortar el canal.

## Commits

1. **Proyeccion meteorologica durable de siete dias** - `e9310b0`
2. **Clima resiliente en el panel** - `c332424`

## Remaining Physical Gate

El app de `c332424` arranco display, LVGL y GT911 en la placa real, pero la NVS de v2 no estaba
provisionada (`nvs_open failed: NOT_FOUND`). Por eso no se atribuye una proyeccion meteorologica
real observada en los modos manual y dormido. El cierre exige provisionar una identidad v2
autorizada sin reemplazar las credenciales actuales, conectar el Home Edge con clima habilitado y
registrar ambos modos sobre el mismo commit.
