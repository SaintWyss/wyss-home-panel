---
status: resolved
trigger: "no quiero que se pueda scrolear por el dispositivo"
created: 2026-07-18T14:18:00Z
updated: 2026-07-18T14:24:00Z
---

# Debug: desplazamiento táctil no deseado

## Symptoms

- Expected: la interfaz de 800x480 permanece fija; arrastrar sobre fondos, tarjetas o botones no desplaza ningún objeto.
- Actual: al arrastrar sobre el dispositivo, algún objeto de la interfaz puede desplazarse.
- Errors: no hay error visible; es un comportamiento táctil de LVGL.
- Timeline: observado en el firmware actualmente instalado.
- Reproduction: arrastrar el dedo sobre la interfaz física.

## Current Focus

- hypothesis: confirmed; los objetos base de LVGL heredan scroll, elasticidad, momentum y chaining.
- test: el simulador recorre el árbol completo y exige `LV_DIR_NONE` sin flags de gesto táctil.
- expecting: el test falla antes del fix y pasa después sin cambiar botones, sliders ni las vistas fuera del modal.
- next_action: compilar el firmware y validar el bloqueo en la pantalla física.

## Evidence

- timestamp: 2026-07-18T14:18:00Z
  observation: `screen`, capas, páginas y tarjetas principales limpian el flag, pero botones, modal y otros widgets no lo hacen de forma uniforme.
- timestamp: 2026-07-18T14:20:00Z
  observation: la regresión del simulador falló contra el árbol original con `la interfaz conserva un objeto desplazable por tacto`.
- timestamp: 2026-07-18T14:24:00Z
  observation: `LV_DIR_NONE` impide que LVGL elija un `scroll_obj`; sliders y botones procesan el puntero sin consultar esa dirección.

## Eliminated

## Resolution

- root_cause: LVGL 8.4 habilita desplazamiento y efectos de gesto por defecto; la UI sólo los anulaba en algunos contenedores.
- fix: recorrer el árbol al terminar `begin()`, bloquear direcciones táctiles y limpiar elasticidad, momentum y chaining.
- verification: TDD rojo/verde, recorrido completo del árbol, capturas visuales deterministas y revisión del manejo de sliders/clicks.
- files_changed: firmware/src/adapters/lvgl_panel_view.cpp, simulator/ui_simulator.cpp, tests/fixtures/ui_visual_manifest.txt
