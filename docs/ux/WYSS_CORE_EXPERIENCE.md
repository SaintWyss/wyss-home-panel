# Experiencia Wyss Core

## Identidad

Yo diseño una presencia futurista propia, no una copia visual de Iron Man. Yo combino un idle tipo HUD ambiental con un modo manual Wyss Core: fondo azul noche, cian como energía, blanco para información, verde para verificación, ámbar para espera y rojo sólo para bloqueo/error.

## Modos

### Wyss durmiendo

Yo muestro un núcleo central que respira lentamente, hora, clima actual, próximo evento y conectividad. Yo reduzco brillo y refresco, pero mantengo WSS y tacto listos. Yo evito sombras, blur, partículas y transformaciones que ya demostraron picos de latencia en el hardware.

Yo despierto cuando:

- yo toco la pantalla;
- yo pulso hablar en Android o PC;
- Wyss propone una confirmación;
- termina un temporizador;
- llega una alerta de prioridad alta;
- cambia a estado degradado que requiere atención.

### Conversación

Yo agrando el núcleo y cambio su patrón según `listening`, `thinking`, `awaiting_confirmation`, `executing`, `verified` o `failed`. Yo muestro una respuesta breve de máximo tres líneas y una acción para ver detalle. Yo no reproduzco audio desde el panel en v2.0.0.

### Manual

Yo entro por toque o botón persistente. Yo organizo la navegación en Inicio, Hogar, Media, Agenda y Sistema. Yo uso tarjetas contextuales y mantengo controles críticos visibles sin scroll.

## Wireframe de idle

```text
┌──────────────────────────────────────────────────────────────────────┐
│  22:14                                           WYSS • EN LÍNEA     │
│                                                                      │
│                         ╭────────────╮                               │
│                      ╭──┤    WYSS    ├──╮                            │
│                      │  │ durmiendo  │  │                            │
│                      ╰──┤     ◉      ├──╯                            │
│                         ╰────────────╯                               │
│                                                                      │
│  24° Despejado          Próximo: Sistemas 18:30       Timer 12:04   │
│                                                                      │
│                       [ MODO MANUAL ]                                │
└──────────────────────────────────────────────────────────────────────┘
```

## Wireframe manual

```text
┌──────────────────────────────────────────────────────────────────────┐
│ WYSS CORE      Inicio  Hogar  Media  Agenda  Sistema     ◉ ONLINE   │
├──────────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐ ┌───────────────┐ ┌─────────────────────────────┐ │
│ │ LIVING        │ │ SPOTIFY       │ │ CLIMA 7 DÍAS                │ │
│ │ ENCENDIDA     │ │ canción       │ │ Hoy 24°  Ma 25°  Mi 21°     │ │
│ │ [OFF] ──●──   │ │ ◀  ▶  ▶▶      │ │ Ju 23°   Vi 26°             │ │
│ └───────────────┘ └───────────────┘ └─────────────────────────────┘ │
│ ┌───────────────────────────────┐ ┌───────────────────────────────┐ │
│ │ AGENDA / RECORDATORIOS        │ │ TIMERS / CÁMARAS              │ │
│ │ 18:30 Sistemas                │ │ Descanso 12:04   Entrada ●    │ │
│ └───────────────────────────────┘ └───────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## Interacciones

- Yo aplico feedback táctil visual en el mismo frame o siguiente.
- Yo no envío órdenes mientras arrastro; yo envío al soltar y hago debounce.
- Yo mantengo pulsación larga para detalle, nunca para una acción destructiva oculta.
- Yo uso modal para B y gate de texto `CONFIRMAR` para C.
- Yo muestro offline/desactualizado junto al dato, no como toast que desaparece.
- Yo conservo toast sólo para resultados secundarios y lo cierro automáticamente.
- Yo permito volver al idle desde cualquier vista con un toque.

## Contenido por módulo

| Módulo | Resumen que yo muestro | Detalle que yo habilito |
| --- | --- | --- |
| Hogar | Luz principal, escena y disponibilidad | Luces, brillo, color, escenas, temporizador |
| Spotify | Canción, artista y play/pause | Progreso, dispositivo, volumen y favoritos |
| Clima | Actual + siete días compactos | Máxima, mínima, precipitación y actualización |
| Agenda | Próximo evento y recordatorio | Día/semana, crear, editar y completar |
| Timers | Más próximo + cantidad | Crear presets, pausar, cancelar y historial inmediato |
| Cámaras | Disponibilidad y último snapshot | Vista de una cámara, nunca mosaico pesado por defecto |
| Sistema | Wyss, Edge, Wi-Fi y latencia | Diagnóstico, versión y acción segura de reconexión |

## Movimiento y rendimiento

Yo animo propiedades baratas: opacidad discreta, color y arcos simples. Yo no animo layout, blur, imágenes grandes ni múltiples sombras. Yo preasigno objetos, actualizo sólo valores cambiados y reduzco el núcleo dormido a 5–10 FPS. Yo mantengo interacción en 30 FPS o más y mido p95/p99 en hardware.

## Accesibilidad

Yo uso objetivos ≥44 px, contraste equivalente a WCAG AA, estado mediante texto además de color y tamaños base ≥14 px en controles. Yo no dependo de gestos ocultos. Yo agrego modo alto contraste y escala de texto en configuración, y pruebo la interfaz a un brazo de distancia.

## Sistema visual

Yo centralizo tokens de color, espaciado, radio, tipografía y movimiento en una única cabecera. Yo genero prototipos en PC con el simulador LVGL antes de flashear. Yo no incorporo assets sin licencia o sin presupuesto de memoria.
