# Phase 1: PR-00 — Baseline reproducible y protección - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase congela y protege el baseline v1: reproduce firmware y Home Edge, valida fixtures,
diagnostica el entorno, bloquea regresiones y registra evidencia física ligada al commit. No
introduce contratos ni capacidades v2.

</domain>

<decisions>
## Implementation Decisions

### Ejecución reproducible
- **D-01:** Usar tooling híbrido aislado por proyecto: `uv.lock` para Python, versiones exactas
  registradas, caches/directorios controlados para PlatformIO y un runner único que refleje CI sin
  perder acceso nativo a USB/serial.
- **D-02:** El runner debe distinguir fallo de código, dependencia, entorno y evidencia; un checkout
  limpio no puede depender silenciosamente de caches globales.

### CI y protección de merges
- **D-03:** Mantener un único workflow con cinco jobs bloqueantes: dominio C++, bridge Python,
  firmware, secretos y documentación. Las acciones permanecen fijadas por SHA completo.
- **D-04:** BASE-05 sólo puede cerrarse cuando GitHub confirme esos checks como requeridos en
  `main`. La ausencia de branch protection mantiene el requisito bloqueado; configurar el remoto
  requiere una acción explícita y auditable.

### Evidencia física
- **D-05:** Un manifest versionado y fail-closed es la autoridad. Cada prueba registra estado
  `NOT_VERIFIED` o `VERIFIED`, commit, fecha, hardware, herramienta, resultado, checksum y referencia
  al artefacto externo; nunca se guardan backups o secretos en Git.
- **D-06:** Notas y simulaciones pueden validar el recolector, pero viven separadas y nunca cierran
  backup, touch/LVGL, Tuya LAN ni smoke físico.

### Claude's Discretion
La forma interna del runner, schema y validadores puede adaptarse al estilo existente mientras
mantenga códigos de salida estables, redacción de secretos y compatibilidad v1.

</decisions>

<open_questions>
## Open Questions

None — all gray areas resolved.

</open_questions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Alcance y aceptación
- `.planning/ROADMAP.md` — goal y criterios de cierre de PR-00.
- `.planning/REQUIREMENTS.md` — requisitos BASE-01..BASE-05.
- `docs/planning/MASTER_PLAN_V2.md` — cambios y aceptación previstos para PR-00.

### Operación y baseline
- `docs/operations/RELEASE_AND_OPERATIONS_V2.md` — separación de comandos operativos y recuperación.
- `README.md` — comandos de calidad y métricas actuales.
- `config/baseline-versions.toml` — versiones y métricas registradas.

### Gates ejecutables
- `.github/workflows/ci.yml` — jobs actuales y pins SHA.
- `tools/doctor.py` — diagnóstico seguro existente.
- `tools/check_docs.py` — gate documental existente.
- `tests/fixtures/protocol/v1/cases.json` — fixture canónico v1.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/doctor.py`: contrato JSON/humano y códigos de salida seguros.
- `bridge/uv.lock`: resolución reproducible del Home Edge.
- `config/baseline-versions.toml`: raíz natural del manifiesto de versiones y métricas.
- `.github/workflows/ci.yml`: cinco fronteras de calidad ya separadas por job.

### Established Patterns
- Python usa `uv --locked`, Ruff, mypy y pytest.
- Dominio host usa CMake/CTest con warnings como errores.
- Firmware usa PlatformIO con plataforma y librerías versionadas.
- Las afirmaciones físicas no se promueven sin evidencia del commit exacto.

### Integration Points
- El runner de baseline conecta manifest, doctor, CMake, bridge, PlatformIO, secret scan y docs.
- El validador de evidencia alimenta verificación GSD y evita cerrar BASE-04 sin hardware.
- Los nombres de jobs de CI deben coincidir con los required checks de GitHub.

</code_context>

<specifics>
## Specific Ideas

Conservar acceso nativo a la placa y usar contenedores sólo como oráculo adicional, no como requisito
para flashing o medición física.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-pr-00-baseline-reproducible-y-proteccion*
*Context gathered: 2026-07-17*
