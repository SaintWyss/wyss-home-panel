---
phase: 20-pr-19-release-v2-final
subsystem: release
tags: [semver, artifacts, checksums, sbom, downgrade, release-gates]
provides:
  - Versiones de producto alineadas en 2.0.0
  - Preparador determinista de candidato bloqueado por default
  - Changelog, compatibilidad, downgrade y checklist final
requirements-partial: [REL-01, REL-02, REL-03]
completed-automated: 2026-07-18
---

# Phase 20: Release v2.0.0 Summary

**La preparación automatizable está implementada; v2.0.0 no está aprobada ni publicable porque
los gates físicos, externos, de firma y protección remota siguen abiertos.**

- Bridge, firmware y SBOM declaran 2.0.0; el protocolo v1 sigue disponible para migración.
- El preparador copia firmware/wheel/SBOM, calcula hashes y registra commit/board/tamaños, pero
  fuerza `BLOCKED_CANDIDATE` y lista cada gate pendiente.
- Ninguna clave se buscó, generó o cambió; la firma real requiere una ruta aprobada por el owner.
- Changelog, matriz de compatibilidad y downgrade seguro están versionados.
- La trazabilidad conserva 51/51 requisitos mapeados, aunque los que exigen evidencia física no se
  marcan falsamente como completos.
- No se creó tag, GitHub Release, push, protección remota ni modificación irreversible del panel.
