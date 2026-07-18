---
status: resolved
trigger: "no quiero que se pueda scrolear por el dispositivo"
created: 2026-07-18T14:18:00Z
updated: 2026-07-18T14:40:46Z
---

# Debug: desplazamiento táctil no deseado

## Symptoms

- Expected: la interfaz de 800x480 permanece fija; arrastrar sobre fondos, tarjetas o botones no desplaza ningún objeto.
- Actual: al arrastrar sobre el dispositivo, algún objeto de la interfaz puede desplazarse.
- Errors: no hay error visible; es un comportamiento táctil de LVGL.
- Timeline: observado en el firmware actualmente instalado.
- Reproduction: arrastrar el dedo sobre la interfaz física.

## Current Focus

- hypothesis: confirmed; además del gesto directo, `SCROLL_ON_FOCUS` puede desplazar un padre al enfocar un control.
- test: el simulador recorre el árbol completo y exige `LV_DIR_NONE` sin flags táctiles ni auto-scroll de foco/teclado.
- expecting: ningún arrastre, foco o flecha puede desplazar la superficie; sliders y clicks conservan coordenadas directas.
- next_action: compilar, flashear y repetir la prueba física.

## Evidence

- timestamp: 2026-07-18T14:18:00Z
  observation: `screen`, capas, páginas y tarjetas principales limpian el flag, pero botones, modal y otros widgets no lo hacen de forma uniforme.
- timestamp: 2026-07-18T14:20:00Z
  observation: la regresión del simulador falló contra el árbol original con `la interfaz conserva un objeto desplazable por tacto`.
- timestamp: 2026-07-18T14:24:00Z
  observation: `LV_DIR_NONE` impide que LVGL elija un `scroll_obj`; sliders y botones procesan el puntero sin consultar esa dirección.
- timestamp: 2026-07-18T14:40:46Z
  observation: la pantalla física todavía se desplazó ocasionalmente; `LV_EVENT_FOCUSED` llama a `lv_obj_scroll_to_view_recursive()` cuando queda `SCROLL_ON_FOCUS`.

## Eliminated

## Resolution

- root_cause: LVGL 8.4 habilita desplazamiento, efectos de gesto y auto-scroll de foco por defecto; la UI sólo los anulaba en algunos contenedores.
- fix: recorrer el árbol al terminar `begin()`, resetear offsets, bloquear direcciones táctiles y limpiar elasticidad, momentum, chaining, auto-scroll de foco y flechas.
- verification: TDD rojo/verde, recorrido completo del árbol, capturas visuales deterministas, revisión del manejo de sliders/clicks y prueba física de seguimiento.
- files_changed: firmware/src/adapters/lvgl_panel_view.cpp, simulator/ui_simulator.cpp, tests/fixtures/ui_visual_manifest.txt
