---
phase: 16-pr-15-ota-recovery
status: cryptographic-and-health-automated-physical-ab-recovery-pending
verified_at: 2026-07-18T01:20:00Z
requirements: [OTA-01, OTA-02]
tested_commit: a3e6470ce20cbb18369c026e9ad22d2e4c6ecb5c
---

# Verification: Phase 16

| Criterion | Evidence | Result |
|---|---|---|
| Manifest/checksum/firma rechazan imagen no autorizada | Ed25519 real, corrupción/tamper/otro signer | PASS AUTOMATED |
| A/B, health boot y rollback ante corte | ledger probado; falta integración física de bootloader | PENDING PHYSICAL |
| Provisioning/backup/restore/rescate conservan config | provisioning existente; backup fábrica; falta round-trip NVS | PENDING PHYSICAL |
| P8 mantiene eFuses/cifrado intactos | ninguna operación o cambio de configuración irreversible | PASS SAFETY GATE |

## Automated evidence

- Python completo: 182 tests PASS; única advertencia externa de deprecación TestClient.
- Ruff, Ruff format y MyPy estricto: PASS.
- Ed25519: imagen exacta PASS; byte agregado, manifest alterado, board incorrecta y segundo signer
  son rechazados.
- Health ledger: promoción sólo con cinco checks; touch fallido e interrupción antes de promoción
  producen rollback; archivo privado 0600.
- Firmware usado como referencia sigue teniendo SHA-256
  `353906395b581e420f6aa2d7f7491c9432aae95a77ebfc24beb5cacf4ddd4607`.

## Physical state and prohibitions

- La pantalla continúa con el firmware original restaurado y funcional; no fue reflasheada.
- No se escribió bootloader, tabla de particiones, OTA slot, NVS, credencial o backup.
- No se ejecutó `espefuse`, Secure Boot ni Flash Encryption. O-06 y P8 siguen abiertos.

## Pending evidence

Diseño/validación de particiones A/B autorizado, carga física, health boot real, firma inválida,
corrupción, corte de energía, rollback conocido, backup/restore/migración NVS y rescate USB.
