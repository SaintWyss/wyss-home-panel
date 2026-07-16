# ADR 0002 — Yo priorizo latencia perceptual cero

## Estado

Yo acepto esta decisión.

## Decisión

Yo pinto un estado optimista antes de la respuesta de red, identifico cada orden y reconcilio con el estado real. Yo restauro el estado anterior después de 2,5 segundos sin confirmación.

## Consecuencias

Yo logro una interfaz fluida sin mentir de forma persistente. Yo acepto un cambio visual transitorio cuando la red o el dispositivo rechazan la orden.

