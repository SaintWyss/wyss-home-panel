# Postura de seguridad — Fase 18

**Commit auditado:** `35701de0ff8ccd657198ff4fb3a3b7db02a3b81d`  
**Fecha:** 2026-07-18T01:40:22Z  
**Alcance:** bridge Python, firmware C++, protocolo v1/v2, dependencias, CI y configuración
remota de la rama principal.

## Resultado ejecutivo

El código implementado no conserva hallazgos críticos o altos conocidos. La publicación sigue
bloqueada por un hallazgo externo alto: `main` todavía no tiene branch protection aplicada en
GitHub. El contrato local ya exige reviews, checks, conversaciones resueltas, prohibición de
force-push y borrado, pero la API remota devolvió protección ausente. Aplicarla requiere el gate
literal de publicación del operador.

La auditoría automatizada cerró parser/fuzz, downgrade, injection, SSRF del proveedor público,
replay, carreras, revocación, scopes, dependencias, SBOM y secret scan. Cámara y acceso remoto no
se consideran superficies activas: siguen deshabilitados hasta resolver O-03 y O-02.

| Severidad | Código implementado | Configuración externa | Residual |
| --- | ---: | ---: | ---: |
| Crítica | 0 | 0 | 0 |
| Alta | 0 | 1 | 0 |
| Media | 0 | 0 | 2 |

## Hallazgo 1 — `main` sin protección remota

- **Severidad:** ALTA
- **Confianza:** 10/10
- **Estado:** VERIFICADO / BLOQUEADO POR GATE DEL OPERADOR
- **Owner:** SaintWyss, owner del repositorio
- **Evidencia:** `.github/required-checks.json` declara la política requerida; la consulta de
  protección de `repos/SaintWyss/wyss-home-panel/branches/main` devolvió todos los controles
  ausentes.
- **Escenario de explotación:** una credencial de maintainer comprometida hace push directo o
  reescribe `main`; al no existir review ni required checks remotos, el cambio evita tests,
  Gitleaks y revisión humana y puede convertirse en firmware o bridge publicado.
- **Impacto:** compromiso de supply chain y despliegue doméstico no revisado.
- **Mitigación inmediata:** no push, tag ni release hasta autorización; conservar el artefacto y
  la pantalla funcional localmente.
- **Corrección:** aplicar exactamente el contrato versionado mediante el flujo de Phase 1 tras
  recibir `APROBAR PUBLICACIÓN Y PROTECCIÓN`, verificarlo por API y recién entonces publicar.
- **Fecha límite:** antes del primer push de este lote y, en todo caso, antes de v2.0.0.

## Riesgos residuales no altos

| Riesgo | Sev. | Owner | Impacto | Mitigación actual | Revisión |
| --- | --- | --- | --- | --- | --- |
| La plataforma ESP32 se obtiene desde un release HTTPS versionado, no desde un digest del ZIP | Media | Maintainer | Un upstream comprometido podría alterar una reconstrucción limpia | Librerías Git por commit, versiones registry exactas, SBOM determinista, CI y firma OTA antes de promoción | Phase 20, antes del tag |
| Token de dispositivo y CA local permanecen en NVS hasta O-06 | Media | Operador | Acceso físico podría extraer una identidad revocable | No hay OAuth/cámara en firmware; token por dispositivo, hash server-side y revocación; Secure Boot/Flash Encryption requieren recovery probado y autorización separada | Gate O-06 antes de producción |

## Evidencia automatizada

- Python: 202 tests PASS; Ruff, format y Mypy PASS.
- C++: 5/5 CTest PASS; 4.000 entradas hostiles adicionales en cada parser Python y C++.
- Firmware: build `SUCCESS`; RAM 150.072 bytes (45,8 %), Flash 1.623.145 bytes (24,8 %),
  binario 1.623.504 bytes, SHA-256
  `a271ddeb6dd6685fe344c76fb041cba1dd5ee01aab891428c06e9943564d3455`.
- Dependency scan: `pip-audit 2.10.1`, 31 paquetes evaluados, 0 vulnerabilidades conocidas.
- SBOM CycloneDX 1.6: 32 componentes, SHA-256
  `f42060c25547eb230cf046d247b80582b89f22d3babc3af6d9127610d87c074b`.
- Secret scan: Gitleaks 8.30.1, 104 commits y 1,66 MB inspeccionados, 0 leaks.
- CI: Actions por SHA, permisos read-only y Gitleaks sobre historial completo; audit y SBOM se
  reproducen en el job bridge.

## STRIDE resumido

| Categoría | Frontera y control |
| --- | --- |
| Spoofing | identidad por cliente, token aleatorio, hash y comparación constante, revocación |
| Tampering | schema estricto, idempotencia/revisión, manifiesto Ed25519 y checksum |
| Repudiation | event log y auditoría de comandos sin secretos |
| Information disclosure | archivos 0600, CSP, no-store, redacción y Gitleaks |
| Denial of service | 8 KiB, profundidad 8, rate limit, backpressure y caches acotados |
| Elevation of privilege | capabilities exactas, allowlists, policy A-D y segunda muralla Wyss |

## Clasificación de datos

- **Restringido:** tokens de host, claves Tuya, claves privadas y OAuth; sólo host/config privada.
- **Confidencial:** agenda, recordatorios, conversación y estado doméstico; persistencia local
  mínima y sin exposición en métricas.
- **Interno:** health, métricas agregadas, IDs seguros y auditoría redactada.
- **Público:** documentación, contratos y assets estáticos sin secretos.

Esta revisión asistida no sustituye una auditoría profesional ni un pentest. Puede omitir fallas
sutiles; antes de una exposición real o de manejar datos de terceros corresponde una evaluación
independiente.
