---
phase: 18-pr-17-hardening-y-suite-adversarial
subsystem: security
tags: [fuzz, ssrf, sbom, dependencies, secrets, supply-chain]
provides:
  - Parsers Python/C++ endurecidos y corpus hostil determinista
  - Allowlist estricta para el proveedor HTTP público
  - SBOM CycloneDX y dependency audit reproducibles en CI
  - Secret scan configurado y dependencias Git de firmware fijadas por commit
requirements-partial: [SEC-01, SEC-02]
completed-automated: 2026-07-18
---

# Phase 18: Hardening Summary

**El alcance automatizable está cerrado; la fase completa y la publicación siguen bloqueadas por
branch protection remota, cámara/remote ausentes y sus gates del operador.**

- Fuzz determinista de 4.000 entradas por parser cubre bytes arbitrarios, profundidad patológica,
  enteros extremos y Unicode inválido sin escapar del contrato de error cerrado.
- Versiones downgrade y confusión `bool/int` se rechazan correctamente; el fuzz encontró y corrigió
  esa clasificación en Python.
- Open-Meteo sólo acepta su origen HTTPS exacto, sin userinfo, query, fragment, path alternativo ni
  redirects.
- Las librerías Git de firmware usan commits inmutables; Python conserva `uv.lock` y `pip-audit`
  exacto en CI.
- El SBOM determinista recorre sólo la clausura runtime Python y las dependencias firmware fijadas.
- Gitleaks usa configuración versionada, action por SHA e historial completo.
- No se activó cámara, VPN, listeners públicos, eFuses, Secure Boot ni Flash Encryption.
