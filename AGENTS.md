<!-- GSD:project-start source:PROJECT.md -->
## Project

**Wyss Home Panel**

Wyss Home Panel es el cliente físico y el Home Edge local de Wyss Home: una pantalla ESP32-S3, un puente FastAPI y adapters domésticos que proyectan y ejecutan capacidades autorizadas por Wyss. La versión 2.0.0 debe convertir el baseline actual en una experiencia multicliente coherente entre PC, Android y panel, con integraciones domésticas, operación recuperable y evidencia de seguridad y rendimiento.

**Core Value:** Toda acción doméstica debe pasar por una única autoridad de política y ejecución de Wyss, conservar coherencia observable entre clientes y fallar de forma segura.

### Constraints

- **Compatibilidad**: v1 debe permanecer funcional durante la migración y v2 debe poder desactivarse o revertirse por incremento.
- **Arquitectura**: ports y contratos preceden a adapters; dominio y aplicación no importan frameworks ni adapters laterales.
- **Autoridad**: Wyss es la única autoridad para planes, política, confirmación, ejecución y auditoría.
- **Seguridad**: fronteras nuevas usan identidad por dispositivo, least privilege, schemas cerrados, allowlists, idempotencia y fail-closed.
- **Datos**: cada dato mutable tiene una sola autoridad y los clientes sólo conservan proyecciones o caches acotados.
- **Rendimiento**: tacto→paint ≤50 ms, UI interactiva ≥30 FPS y operaciones LAN críticas p95 ≤150 ms cuando haya hardware para medir.
- **Evidencia**: cada fase registra tests automatizados, checks estáticos, rollback y evidencia física cuando corresponda.
- **Cambios irreversibles**: no se queman eFuses ni se cambian credenciales, cuentas, particiones o datos persistentes sin autorización explícita.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
