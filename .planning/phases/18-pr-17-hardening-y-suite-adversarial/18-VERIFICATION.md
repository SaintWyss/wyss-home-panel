---
phase: 18-pr-17-hardening-y-suite-adversarial
status: automated-security-passed-external-high-gate-open
verified_at: 2026-07-18T01:40:22Z
requirements: [SEC-01, SEC-02]
tested_commit: 35701de0ff8ccd657198ff4fb3a3b7db02a3b81d
---

# Verification: Phase 18

| Criterion | Evidence | Result |
| --- | --- | --- |
| Parser/fuzz, replay, downgrade, SSRF, injection, carreras, revocación y scopes | Suite nueva + tests previos mapeados | PASS AUTOMATED KNOWN SURFACES |
| Dependency scan, SBOM y secret scan reproducibles | CI, generator, pip-audit y Gitleaks | PASS AUTOMATED |
| Sin crítico/alto abierto | Código 0; branch protection remota ausente | BLOCKED EXTERNAL HIGH |
| Rollback conserva segunda muralla | flags/disabled adapters + tests de policy/revocación/scopes | PASS AUTOMATED |

## Matriz adversarial

| Riesgo | Evidencia |
| --- | --- |
| Parser/fuzz | `test_security_adversarial.py`; `protocol_v2_fixture_tests.cpp` |
| Replay/idempotencia | `test_event_backbone.py`, `test_light_service.py`, `test_media_service.py` |
| Downgrade/type confusion | `test_protocol_rejects_downgrade_and_type_confusion` |
| SSRF/redirect | `test_open_meteo_rejects_ssrf_origins_and_paths` |
| Injection | `test_protocol_rejects_command_injection_before_policy_or_adapter` |
| Carreras | `test_concurrent_appends_preserve_unique_monotonic_revisions` y CAS de planes |
| Revocación | `test_rotate_invalidates_old_token_and_revoke_is_immediate`; API next-message |
| Scopes | Spotify/Calendar exactos y capabilities por cliente |
| Dependencias | pip-audit 31/0; commits Git exactos; CI bloqueante |
| SBOM | CycloneDX 1.6, 32 componentes, hash registrado |
| Secretos | Gitleaks 104 commits/0 findings; redacción de métricas y CLI |

## Bloqueos explícitos

1. `main` no tiene protección remota: requiere el gate literal de Phase 1 antes del push.
2. Cámara no identificada: no existe superficie activa ni adapter que pueda auditarse físicamente.
3. Acceso remoto no aprobado: el sistema permanece LAN-only sin VPN/listener público.
4. O-06 y recovery físico siguen pendientes; no se tocaron eFuses ni cifrado.
