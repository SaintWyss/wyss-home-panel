# Wyss Home Panel

## What This Is

Wyss Home Panel es el cliente físico y el Home Edge local de Wyss Home: una pantalla ESP32-S3, un puente FastAPI y adapters domésticos que proyectan y ejecutan capacidades autorizadas por Wyss. La versión 2.0.0 debe convertir el baseline actual en una experiencia multicliente coherente entre PC, Android y panel, con integraciones domésticas, operación recuperable y evidencia de seguridad y rendimiento.

## Core Value

Toda acción doméstica debe pasar por una única autoridad de política y ejecución de Wyss, conservar coherencia observable entre clientes y fallar de forma segura.

## Requirements

### Validated

- ✓ El firmware ESP32-S3 compila con PlatformIO y mantiene dominio, aplicación, ports y adapters separados — existente.
- ✓ El panel renderiza una interfaz LVGL 8.4 y aplica estado optimista con rollback — existente.
- ✓ El bridge FastAPI separa dominio, aplicación y adapters para Wyss, Tuya y Home Assistant — existente.
- ✓ El camino rápido de luces aplica allowlist, rate limit e idempotencia — existente.
- ✓ Existen tests de dominio C++ y tests Python del servicio de sesión — existente.
- ✓ Existen herramientas de identidad, instalación del bridge y aprovisionamiento del panel — existente.

### Active

- [ ] Congelar y verificar una línea base reproducible antes de evolucionar el runtime.
- [ ] Introducir contratos v2 compatibles con v1 y fixtures dorados Python/C++.
- [ ] Proveer identidad por dispositivo, pairing, revocación y eventos reanudables.
- [ ] Sincronizar proyecciones coherentes entre PC, Android y panel.
- [ ] Entregar la experiencia visual final de Wyss Core con accesibilidad y presupuestos físicos.
- [ ] Completar luces, conversación, voz push-to-talk, Spotify, clima, Calendar, recordatorios, temporizadores y cámaras detrás de ports.
- [ ] Habilitar acceso remoto privado, OTA recuperable, observabilidad, hardening, soak y release v2.0.0 trazable.

### Out of Scope

- Wake word y TTS — la entrada de voz será push-to-talk y la salida del panel será textual.
- Exposición pública o port forwarding — el acceso remoto será exclusivamente mediante red privada autenticada.
- Acceso directo de clientes o adapters al executor de Wyss — rompería la autoridad única y la segunda muralla de política.
- Credenciales domésticas, OAuth o claves persistidas en firmware o logs — permanecen en el Home Edge o proveedores seguros.
- Declarar hardware o servicios externos como verificados sin evidencia física del commit exacto — se registrarán como bloqueos explícitos.

## Context

- El repositorio contiene firmware C++/Arduino para Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2 y un bridge Python/FastAPI.
- El baseline documentado incluye LVGL/touch de 0,4 ms, Tuya LAN de 22–41 ms, RAM de 29,3 % y Flash de 24 %; PR-00 debe reproducir o reemplazar estas cifras con evidencia comparable.
- La arquitectura objetivo, protocolo, ownership de datos, amenazas, UX, verificación, operaciones y plan PR-00→PR-19 están definidos en `docs/`.
- El código y la documentación fueron indexados en un grafo local de 721 nodos y 1.066 relaciones para orientar dependencias.
- La placa, luz real, Android, cuentas Spotify/Google, cámara y red remota son dependencias externas que requieren smoke físico o credenciales del operador; nunca se simularán como evidencia real.

## Constraints

- **Compatibilidad**: v1 debe permanecer funcional durante la migración y v2 debe poder desactivarse o revertirse por incremento.
- **Arquitectura**: ports y contratos preceden a adapters; dominio y aplicación no importan frameworks ni adapters laterales.
- **Autoridad**: Wyss es la única autoridad para planes, política, confirmación, ejecución y auditoría.
- **Seguridad**: fronteras nuevas usan identidad por dispositivo, least privilege, schemas cerrados, allowlists, idempotencia y fail-closed.
- **Datos**: cada dato mutable tiene una sola autoridad y los clientes sólo conservan proyecciones o caches acotados.
- **Rendimiento**: tacto→paint ≤50 ms, UI interactiva ≥30 FPS y operaciones LAN críticas p95 ≤150 ms cuando haya hardware para medir.
- **Evidencia**: cada fase registra tests automatizados, checks estáticos, rollback y evidencia física cuando corresponda.
- **Cambios irreversibles**: no se queman eFuses ni se cambian credenciales, cuentas, particiones o datos persistentes sin autorización explícita.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mantener arquitectura hexagonal en firmware, Edge y Wyss | Permite adapters reemplazables y contract tests sin acoplar dominio a infraestructura | ✓ Good |
| Wyss conserva autoridad única A–D | Evita bypass de política entre panel, Android, PC e integraciones | ✓ Good |
| Sincronización v2 por snapshot inicial y deltas revisionados | Reduce polling y permite reconexión multicliente coherente | — Pending |
| Acceso remoto sólo por Tailscale o WireGuard con ACL por dispositivo | Evita exponer servicios domésticos a Internet | — Pending |
| Voz push-to-talk sin wake word ni TTS | Reduce privacidad, consumo y superficie operativa | — Pending |
| Entrega en PRs PR-00→PR-19 con rollback explícito | Controla el riesgo y preserva el sistema que ya funciona | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-17 after initialization*
