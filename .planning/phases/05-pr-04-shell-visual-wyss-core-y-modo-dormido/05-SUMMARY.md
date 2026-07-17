---
phase: 05-pr-04-shell-visual-wyss-core-y-modo-dormido
subsystem: embedded-ui
tags: [lvgl, simulator, accessibility, visual-regression, sleep-mode]
requires:
  - phase: 04-pr-03-projection-store-y-sincronizacion-multicliente
    provides: proyecciones revisionadas y convergencia automatizada
provides:
  - Shell Wyss Core con Inicio, Hogar, Media, Agenda y Sistema
  - Modos manual, conversacional y dormido con refresco diferenciado
  - Simulador headless sobre el LVGL 8.4.0 exacto del firmware
  - Baseline visual determinista de nueve estados
affects: [lights, conversation, integrations, observability]
requirements-completed: [UI-01, UI-03]
requirements-partial: [UI-02]
completed-automated: 2026-07-17
---

# Phase 5: Wyss Core shell and sleeping mode Summary

**La experiencia y su regresión automatizada están completas; faltan mediciones en la placa y la decisión O-05.**

## Accomplishments

- Centralizó colores, geometría, objetivos táctiles, refresco y brillo en tokens compartidos.
- Implementó navegación consistente entre Inicio, Hogar, Media, Agenda y Sistema.
- Conservó el control optimista de la luz y agregó acciones rápidas mediante el funnel de Wyss.
- Separó el ciclo conversacional y la confirmación en superficies explícitas sin alterar la política.
- Implementó reposo después de cinco minutos, escena atenuada y refresco configurado a 8 FPS.
- Mantuvo modo activo en 30 FPS nominales y objetivos táctiles de al menos 44 px.
- Corrigió texto largo, estados offline, foco visible y caracteres no disponibles en la fuente embebida.
- Elevó el heap LVGL de 48 a 96 KiB después de reproducir el agotamiento; el simulador conserva
  50.760 bytes libres al finalizar los nueve escenarios.
- Integró las capturas visuales al baseline y fija cambios intencionales mediante hashes RGB.

## Commits

1. **Tokens y contratos accesibles** - `1cf7a0b`
2. **Shell, conversación y reposo** - `e76b02f`
3. **Simulador y regresión visual** - `8f8e4a5`

## Physical Setup Pending

- Medir tacto→paint p95, FPS activo/reposo, energía, temperatura y legibilidad en la placa exacta.
- Confirmar RAM/Flash en ejecución, no sólo el tamaño estático del binario.
- El backlight configurado en `firmware/include/esp_panel_board_custom_conf.h` usa
  `SWITCH_EXPANDER`, que sólo ofrece on/off. El valor lógico de 18 % no demuestra atenuación ni
  ahorro físico; O-05 debe decidir si la escena oscura basta o si el hardware exige otro mecanismo.
- Registrar la decisión final de brillo/FPS en una ADR ligada al commit físicamente probado.

