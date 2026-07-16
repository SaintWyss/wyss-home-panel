# Rendimiento

## Presupuesto

Yo uso estos objetivos en una red local estable:

| Trayecto que mido | p50 | p95 | Límite |
|---|---:|---:|---:|
| toque → cambio visual | ≤ 16 ms | ≤ 33 ms | 50 ms |
| orden → foco Tuya local | ≤ 35 ms | ≤ 80 ms | 150 ms |
| orden → reconciliación visual | ≤ 60 ms | ≤ 120 ms | 250 ms |
| ciclo LVGL sin redibujar | ≤ 1 ms | ≤ 3 ms | 8 ms |
| cuadro visual | 30 fps | 30 fps | sin caídas debajo de 24 fps |

## Técnicas

- Yo respondo en `LV_EVENT_PRESSED` para las acciones discretas.
- Yo actualizo el slider localmente y envío una sola orden al soltar.
- Yo corro LVGL en el núcleo 1 y WebSocket/Wi-Fi en el núcleo 0.
- Yo uso dos framebuffers y un bounce buffer de diez líneas para evitar tearing.
- Yo redibujo únicamente valores cambiados y desactivo animaciones costosas.
- Yo desactivo el ahorro Wi-Fi mientras la pantalla está activa y apago la retroiluminación después de cinco minutos inactivos.
- Yo uso mensajes JSON compactos, colas acotadas y conexiones persistentes.

## Medición

Yo conservo como línea de base las mediciones físicas del firmware anterior: 0,4 ms por ciclo LVGL estable, 0,4 ms de lectura táctil y 22–41 ms para Tuya LAN. Yo no presento esos números como medición del firmware nuevo hasta volver a ejecutarlos en la placa.

Yo registro cada `round_trip_ms` en `execution.update`. Yo considero una regresión cualquier p95 superior al presupuesto durante 200 acciones consecutivas.

