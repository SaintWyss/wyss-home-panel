# ADR-0006 — Yo uso push-to-talk desde PC y Android

**Estado:** aceptada para v2.0.0.

## Contexto

Yo confirmé que el módulo disponible es un sensor de sonido, no un micrófono capaz de entregar voz. Yo ya tengo micrófonos más capaces en PC y Android.

## Decisión

Yo capturo mediante botón en PC y Android, transcribo fuera del ESP32, permito revisar el texto y muestro la respuesta escrita en la pantalla. Yo no implemento wake word, escucha permanente ni TTS en v2.0.0.

## Consecuencias

Yo mejoro privacidad, precisión y carga del panel. Yo dependo de al menos un cliente con micrófono para voz, pero mantengo texto como fallback completo.
