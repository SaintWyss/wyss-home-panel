# Registro de riesgos

## Uso

Yo reviso este registro en cada PR y antes de promover una release. Yo no acepto riesgo crítico/alto sin mitigación verificada o decisión explícita del owner.

| Id | Riesgo | Sev. | Prob. | Mitigación que yo planifico | Gate |
| --- | --- | --- | --- | --- | --- |
| R-01 | Yo podría crear un segundo path que evada policy | Crítica | Media | Yo mantengo Wyss como autoridad, contrato único y tests de bypass. | PR-01/06/17 |
| R-02 | Yo podría exponer credenciales desde ESP/logs | Crítica | Media | Yo concentro secretos en host, redacto y escaneo. | Todos/PR-17 |
| R-03 | Yo podría perder control por actualización fallida | Alta | Media | Yo uso A/B firmada, health boot, rollback y USB rescue. | PR-15 |
| R-04 | Yo podría degradar la fluidez con UI/HUD | Alta | Media | Yo uso tokens baratos, diff rendering y budgets físicos. | PR-04/16 |
| R-05 | Yo podría mostrar estado optimista falso | Alta | Media | Yo reconcilio con revisión real y rollback 2,5 s. | PR-05 |
| R-06 | Yo podría ejecutar dos veces por reconnect | Alta | Media | Yo uso idempotencia durable y entrega al menos una vez. | PR-02/03/12 |
| R-07 | Yo podría exponer cámara o permitir SSRF | Crítica | Media | Yo configuro endpoint administrativamente, mantengo LAN y proxy Edge. | PR-13/17 |
| R-08 | Yo podría perder timers al reiniciar | Media | Alta | Yo persisto antes de ack y recupero con UTC+monotónico. | PR-12 |
| R-09 | Yo podría exceder cuotas/rate limits | Media | Alta | Yo cacheo, hago sync incremental y backoff. | PR-08/09/10 |
| R-10 | Yo podría romper OAuth por cambios de proveedor | Alta | Media | Yo aíslo adapters, contract tests y reautorización. | PR-08/10 |
| R-11 | Yo podría filtrar audio/conversación | Alta | Baja | Yo uso push-to-talk, borrado de buffer y minimización. | PR-07/17 |
| R-12 | Yo podría dejar la casa expuesta en Internet | Crítica | Baja | Yo prohíbo port forwarding y uso VPN/ACL. | PR-14/17 |
| R-13 | Yo podría fragmentar demasiado repos/servicios | Media | Media | Yo separo por dominio dentro de dos repos y extraigo sólo con independencia. | ADR-0005 |
| R-14 | Yo podría agotar PSRAM/Flash | Alta | Media | Yo impongo size gates, assets acotados y margen OTA. | PR-04/15/16 |
| R-15 | Yo podría depender de una cámara incompatible | Media | Alta | Yo postergo adapter hasta identificar hardware y mantengo port genérico. | PR-13 |
| R-16 | Yo podría duplicar notificaciones | Media | Media | Yo uso event id, ack y dedupe estable. | PR-11/12 |

## Criterio de cierre

Yo cierro un riesgo únicamente cuando existe control implementado, test, evidencia y owner de operación. Yo no lo cierro porque “parece poco probable”.

## Residuales de seguridad antes de release

| Id | Estado | Owner | Impacto residual | Mitigación vigente | Fecha de revisión |
| --- | --- | --- | --- | --- | --- |
| R-02 | Mitigado automatizado | Maintainer | Una regresión podría volver a exponer secretos | Gitleaks, redacción, 0600 y CI; 104 commits sin leaks | Cada PR y Phase 20 |
| R-03 | Bloqueado físico | Operador | Una OTA real podría requerir rescate | Firma/health lógico listo; A/B, backup, restore y USB pendientes | Antes de OTA real |
| R-07 | Feature ausente | Operador | Hardware/protocolo desconocido podría introducir SSRF | Cámara deshabilitada; no existe adapter ni credencial | Tras resolver O-03 |
| R-12 | Feature ausente | Operador | Una configuración remota incorrecta podría exponer la LAN | LAN-only, sin port forwarding ni listener público | Tras resolver O-02 |
| R-17 | Gate externo alto | Repo owner | Push directo podría evitar CI/review | No publicar; aplicar contrato de branch protection tras gate literal | Antes del próximo push |
| R-18 | Residual medio | Operador | Acceso físico podría extraer token revocable desde NVS | Token por dispositivo, sin OAuth/cámara, revocación; O-06 separado | Antes de producción |
