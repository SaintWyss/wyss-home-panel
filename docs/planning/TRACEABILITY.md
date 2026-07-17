# Matriz de trazabilidad

## Uso

Yo actualizo esta matriz en cada PR. Yo no marco una fila como completa sin enlace a test automatizado y, cuando corresponde, evidencia física del commit exacto.

| Requisito | PR dueño | Test automatizado | Evidencia física | Estado inicial |
| --- | --- | --- | --- | --- |
| RF-01 Conversación multicliente | PR-03/06 | contract + integration | PC/Android/Panel | Planificado |
| RF-02 Push-to-talk | PR-07 | `test_voice_service` + `test_v2_api` | Mic PC + Android | Automatizado; O-01/física pendiente |
| RF-03 Luces | PR-05 | domain/contract/protocol | LEDVANCE real | Baseline existente; migración pendiente |
| RF-04 Spotify | PR-08 | `test_media_adapters` + `test_media_service` + `test_v2_api` | Cuenta Premium real | Automatizado; O-07/cuenta pendiente |
| RF-05 Clima | PR-09 | provider/cache/timezone | Panel real | Planificado |
| RF-06 Calendar | PR-10 | OAuth/sync/CRUD/policy | Calendar real | Planificado |
| RF-07 Temporizadores | PR-12 | clock/recovery/idempotency | Android notification | Planificado |
| RF-08 Cámaras | PR-13 | adapter/SSRF/no-retention | Cámara real | Hardware pendiente |
| RF-09 Modo dormido | PR-04 | UI state/screenshot | FPS/brillo/energía | Planificado |
| RF-10 Modo manual | PR-04 | navigation/accessibility | Touch real | Planificado |
| RF-11 Sincronización | PR-02/03 | reconnect/replay/conflict | Tres clientes | Planificado |
| RF-12 Actualización/recuperación | PR-15 | manifest/migration | OTA/corte/USB | Planificado |
| RNF-01/02 Latencia | PR-05/16 | benchmark harness | 1.000 muestras | Baseline parcial |
| RNF-03 Fluidez | PR-04/16 | simulator metrics | Panel p95/p99 | Baseline parcial |
| RNF-04 Arranque | PR-16 | boot instrumentation | Panel cold boot | Planificado |
| RNF-05 Disponibilidad | PR-03/16/18 | fault injection | Soak | Planificado |
| RNF-06 Seguridad | PR-02/17 | adversarial suite | Pair/revoke | Planificado |
| RNF-07 Privacidad | PR-07/17 | borrado/no-store/no implicit send | Permisos/audio | PR-07 automatizado; física pendiente |
| RNF-08 Resiliencia | PR-18 | chaos/soak | 72 h | Planificado |
| RNF-09 Recursos | PR-04/16 | size/heap gates | Panel | Baseline: RAM 29,3 %, Flash 24 % |
| RNF-10 Mantenibilidad | PR-01 | import/contract gates | N/A | Arquitectura base existente |
| RNF-11 Accesibilidad | PR-04 | static/UI tests | Revisión física | Planificado |
| RNF-12 Sostenibilidad | PR-04/16 | traffic/power | Medición | Planificado |

## Evidencia final

Yo enlazaré desde cada fila el workflow, reporte, captura o acta de smoke. Yo conservaré artefactos de release, hashes y versiones. Yo trataré “hardware pendiente” como bloqueo de release, no como éxito parcial oculto.
