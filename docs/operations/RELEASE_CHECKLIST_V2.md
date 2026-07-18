# Checklist de release v2.0.0

Una release sólo está aprobada cuando todas las casillas están completas sobre el mismo commit.
El candidato actual no cumple todavía los gates físicos/externos y no debe etiquetarse ni
publicarse.

## Automatización preparada

- [x] versiones de firmware, bridge, SBOM y changelog alineadas en 2.0.0;
- [x] CI, Ruff, Mypy, Pytest, CTest, build ESP32, dependency audit y secret scan definidos;
- [x] wheel, firmware, SBOM y checksums componibles por `tools/prepare_release.py`;
- [x] candidato marcado `BLOCKED_CANDIDATE` y `RELEASE_BLOCKED` por defecto;
- [x] compatibilidad, límites, operación, soak y downgrade documentados;
- [x] 51/51 requisitos mapeados y enlazados a test/verificación o gate físico/externo explícito,
  con contrato ejecutable en CI.

## Gates que bloquean publicación

- [ ] branch protection y required checks aplicados remotamente tras recibir la frase literal
  `APROBAR PUBLICACIÓN Y PROTECCIÓN`;
- [ ] CI remoto verde sobre el commit candidato;
- [ ] manifest de firmware firmado con la clave de release autorizada y verificado con la clave
  pública de producción;
- [ ] soak físico continuo de 72 horas y matriz de fallos de red/energía;
- [ ] backup/restore, upgrade v1, rollback OTA y downgrade ensayados;
- [ ] O-01/O-02/O-03/O-04/O-05/O-06/O-07 resueltos donde apliquen;
- [ ] smoke del mismo commit en PC, Android, panel, luz, Spotify, Calendar, clima, timer, reminder,
  notificación y cámara, o exclusión formal de alcance aprobada por el owner;
- [ ] cero hallazgos críticos/altos, incluida la protección de `main`;
- [ ] tag anotado `v2.0.0`, GitHub Release y artefactos publicados sólo después de todo lo anterior.

## Comandos de candidato local

```bash
uv build --project bridge --out-dir dist/wheel
python tools/generate_sbom.py --output dist/wyss-home-panel-2.0.0.cdx.json
python tools/prepare_release.py \
  --output dist/release/v2.0.0 \
  --firmware .pio/build/waveshare_esp32_s3_touch_lcd_7/firmware.bin \
  --bridge-wheel dist/wheel/wyss_home_panel_bridge-2.0.0-py3-none-any.whl \
  --sbom dist/wyss-home-panel-2.0.0.cdx.json \
  --source-commit "$(git rev-parse HEAD)"
```

La firma se realiza después con `wyss-firmware-release create-manifest` y una ruta de clave
proporcionada explícitamente por el operador. El preparador no busca, genera ni sustituye claves.
