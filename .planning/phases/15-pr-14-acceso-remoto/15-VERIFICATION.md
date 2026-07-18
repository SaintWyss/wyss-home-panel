---
phase: 15-pr-14-acceso-remoto
status: blocked-before-implementation-o02
verified_at: 2026-07-18T01:10:00Z
requirements: [REMOTE-01, REMOTE-02]
---

# Verification: Phase 15

La fase no entra en implementación porque O-02 exige que el operador decida primero si habilita
acceso remoto y, en caso afirmativo, seleccione Tailscale o WireGuard después de evaluar Android,
ACL, DNS y recuperación. Esa decisión no puede inferirse del objetivo general.

## Preserved safe state

- No se instaló ni configuró VPN alguna y no se crearon claves privadas.
- No se habilitó port forwarding, listener público, DNS remoto ni regla de firewall.
- El sistema permanece LAN-only y la identidad revocable existente no se amplió.
- La ADR 0008 continúa registrando la decisión como pendiente, sin default encubierto.

## Evidence required to resume

Decisión explícita de habilitar o mantener deshabilitado el acceso remoto y, si se habilita, la
elección Tailscale/WireGuard. Después se requieren ACL/DNS por dispositivo, datos móviles,
revocación, pérdida de VPN, rollback y scan externo sobre el mismo commit.
