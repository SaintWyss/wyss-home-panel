---
phase: 02-pr-01-contratos-y-arquitectura-v2
subsystem: architecture
tags: [protocol-v2, ports, fixtures, architecture, cpp, python]
requires:
  - phase: 01-pr-00-baseline-reproducible-y-protecci-n
    provides: baseline reproducible y fixtures v1
provides:
  - Doce ports pequeños de capacidades sin adapters reales
  - Envelope v2 acotado con parsers Python/C++ equivalentes
  - Fixtures compartidos y gate de límites hexagonales
affects: [identity, events, projections, integrations]
key-files:
  created: [bridge/src/wyss_panel_bridge/ports_v2.py, bridge/src/wyss_panel_bridge/domain/protocol_v2.py, firmware/include/wyss/protocol/envelope_v2.hpp, tools/check_architecture.py]
  modified: [CMakeLists.txt, scripts/verify_baseline.sh, .github/workflows/ci.yml]
requirements-completed: [ARCH-01, ARCH-02, PROTO-01, PROTO-02, PROTO-03]
duration: 17min
completed: 2026-07-17
---

# Phase 2: Contratos y arquitectura v2 Summary

**Ports estables y envelope v2 cruzado, sin activar consumidores ni alterar el runtime v1.**

## Accomplishments

- Definió Home, Light, Projection, ClientEvent, Media, Weather, Calendar, Reminder, Timer,
  Notification, Speech y Camera ports sin adapters.
- Implementó parsers v2 Python/C++ con 8 KiB, profundidad 8, duplicados, replay, revisión,
  snapshots, errores y tipos cerrados sobre los mismos 17 fixtures.
- Agregó un gate AST/include que bloquea dependencias hexagonales inválidas en CI y baseline.
- Conservó el parser C++ detrás de `WYSS_ENABLE_PROTOCOL_V2`; producción v1 mantiene exactamente
  96.048 bytes RAM y 1.574.853 bytes Flash.

## Commits

1. **Ports y DTOs v2** - `c4cc1fc`
2. **Contrato cruzado Python/C++** - `fe8c989`
3. **Límites arquitectónicos y compatibilidad v1** - `be0306e`

## Verification

- 46 pruebas Python PASS.
- 3 pruebas C++ PASS, incluidos fixtures v1 y v2.
- Ruff, formato, mypy, arquitectura, doctor y documentación PASS.
- PlatformIO ESP32-S3 PASS con consumo v1 sin cambio.

## External Setup

None. Esta fase es completamente automatizable y no activa adapters reales.

---
*Phase: 02-pr-01-contratos-y-arquitectura-v2*
*Completed: 2026-07-17*
