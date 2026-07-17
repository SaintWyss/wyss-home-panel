# Evidencia PR-00

Este directorio conserva únicamente metadata sanitizada y ligada al commit probado. El manifest
empieza en `NOT_VERIFIED`; sólo una observación física o externa real puede promover cada entrada.
Fixtures, simuladores, notas del operador y ejecuciones sobre otro SHA nunca cierran BASE-04.

Los binarios de backup, dumps, capturas sin sanitizar y artefactos de hardware permanecen fuera del
repositorio. Aquí se registra una referencia opaca y su SHA-256, nunca el archivo, su ruta absoluta,
credenciales, tokens, claves locales, certificados privados ni datos sensibles. El validador rechaza
campos extra, rutas absolutas, secretos y procedencia simulada.

Flujo previsto:

1. CI verifica el commit y la protección de `main`.
2. `--bind-from docs/evidence/pr-00/branch-protection.json` liga el manifest al SHA exacto.
3. El operador realiza las pruebas con el panel y la luz reales.
4. `python tools/check_baseline_evidence.py` retorna 0 sólo cuando todo está `VERIFIED`.

Hasta completar los pasos físicos, `./scripts/verify_baseline.sh all` retorna 40 de forma deliberada.
