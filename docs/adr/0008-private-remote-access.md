# ADR-0008 — Yo no publico Wyss Home en Internet

**Estado:** aceptada como default; activación remota pendiente de decisión operativa.

## Contexto

Yo quiero manejar el hogar desde Android y puedo necesitar acceso fuera de la Wi-Fi. Abrir puertos expone identidad, agenda, cámaras y ejecución.

## Decisión

Yo uso LAN TLS por default. Para remoto yo uso Tailscale/WireGuard con ACL por dispositivo. Yo prohíbo port forwarding, UPnP y endpoints públicos propios en v2.0.0.

## Consecuencias

Yo reduzco superficie de ataque y mantengo local-first. Yo agrego dependencia opcional de una VPN y debo documentar recovery/revocación.
