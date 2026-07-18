---
phase: 19-pr-18-beta-diaria-y-soak
status: automated-soak-passed-physical-soak-blocked
verified_at: 2026-07-18T01:47:30Z
requirements: [SOAK-01, SOAK-02]
tested_commit: a271ea5afea2beb7b356358b8a55f50dc104c180
---

# Verification: Phase 19

| Criterion | Evidence | Result |
| --- | --- | --- |
| 1.000 reconnects, 500 brightness, 100 timers | `wyss-soak` + `test_soak.py` | PASS AUTOMATED ACCELERATED |
| Fault injection provider/proceso | fallo cerrado + recuperación + 2 recreaciones | PASS AUTOMATED |
| 72 horas y fallos red/energía reales | requiere hardware y tiempo continuo | BLOCKED PHYSICAL |
| Upgrade v1, backup/restore y rollback | requiere autorización y matriz real | BLOCKED PHYSICAL |

## Resultado exacto

```json
{"brightness_changes":500,"crashes":0,"duplicate_events":0,"elapsed_seconds":1.626,"final_brightness":95,"ghost_states":0,"latest_event_id":704,"notification_deliveries":100,"process_restarts_injected":2,"provider_failures_injected":1,"reconnections":1000,"status":"PASS","timer_completions":100}
```

## Regresión

- Ruff format/check: PASS.
- Mypy strict: PASS, 61 source files.
- Pytest: PASS, 203 tests; una advertencia deprecada de Starlette/httpx2 ajena al cambio.
- CMake/CTest con CMake aislado por `uvx`: PASS, 5/5.
- Firmware no se recompiló ni flasheó porque la fase sólo modifica Python/tests/docs; el build
  firmado anterior continúa registrado en Phase 18.

## Bloqueos explícitos

1. `SOAK-01`: faltan 72 horas continuas, red/energía reales, luz, Android y panel sobre el mismo
   commit.
2. `SOAK-02`: faltan backup/restore, upgrade v1 y downgrade físicos; no se tocan NVS ni firmware
   sin el procedimiento y autorización correspondientes.
3. Cámara, VPN, Spotify y Google dependen de gates/hardware/cuentas aún ausentes y por ello no
   pueden formar una matriz E2E completa.
