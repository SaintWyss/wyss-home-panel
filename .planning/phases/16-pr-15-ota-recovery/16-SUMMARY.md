---
phase: 16-pr-15-ota-recovery
subsystem: ota
tags: [ed25519, manifest, checksum, health, rollback]
provides:
  - Manifest canónico firmado y ligado a board, versión, commit, tamaño y SHA-256
  - Health ledger durable con promoción total y rollback por fallo o interrupción
requirements-partial: [OTA-01, OTA-02]
completed-automated: 2026-07-18
---

# Phase 16: OTA y recovery Summary

**La frontera criptográfica y la decisión de promoción están verificadas; A/B, corte de energía,
backup/restore NVS y rescate USB permanecen físicos y no se simulan como completados.**

## Accomplishments

- Firma el manifest canónico con Ed25519 mediante OpenSSL y liga versión, board exacta, commit de
  40 hex, tamaño y SHA-256 de la imagen.
- Verifica antes de stage y rechaza imagen alterada, manifest manipulado, board incompatible,
  base64/algoritmo inválidos y clave pública de otro firmante sin mostrar stderr criptográfico.
- Persiste un ledger 0600 mediante reemplazo atómico. Una imagen candidata sólo se promueve
  después de boot, display, touch, red y handshake saludables.
- Un health negativo revierte inmediatamente; un proceso reiniciado con candidato incompleto lo
  clasifica como corte/interrupción y ordena rollback, sin promover por ausencia de evidencia.
- Expone `wyss-firmware-release create-manifest|verify` como herramienta reproducible. No contiene
  claves y no escribe la placa.
- Conserva el provisioning USB existente y el backup de fábrica verificado. No introduce comandos
  de exportación de secretos por serial ni afirma backup NVS sin prueba física.

## Remaining physical evidence

Particiones A/B reales, boot health integrado, firma inválida/corrupción/corte de energía en placa,
backup/restore/migración NVS, rescate USB e idempotencia física. Secure Boot, Flash Encryption y
eFuses requieren autorización separada y permanecen intactos.
