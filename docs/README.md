# Índice de producto Wyss Home

Yo uso este índice como entrada canónica al diseño final de Wyss Home v2.0.0. Yo separo cada documento por audiencia y evito duplicar decisiones.

| Documento | Decisión que yo concentro |
| --- | --- |
| [Visión y PRD](product/PRODUCT_REQUIREMENTS.md) | Yo fijo alcance, usuarios, requisitos y definición de terminado. |
| [Arquitectura E2E](architecture/END_TO_END_ARCHITECTURE.md) | Yo fijo límites, hexágonos, despliegue y UML. |
| [Protocolo v2](contracts/PROTOCOL_V2.md) | Yo fijo mensajes, idempotencia, sincronización y compatibilidad. |
| [Propiedad de datos](data/DATA_OWNERSHIP.md) | Yo fijo una única fuente de verdad para cada dato. |
| [Experiencia Wyss Core](ux/WYSS_CORE_EXPERIENCE.md) | Yo fijo el modo dormido, manual, conversación y accesibilidad. |
| [Integraciones](integrations/INTEGRATION_CATALOG.md) | Yo fijo Spotify, clima, Calendar, recordatorios, temporizadores, luces, voz y cámaras. |
| [Seguridad](security/THREAT_MODEL_V2.md) | Yo fijo amenazas, controles, privacidad y respuesta. |
| [Verificación](testing/VERIFICATION_STRATEGY_V2.md) | Yo fijo pirámide, contratos, hardware y gates. |
| [Operación y release](operations/RELEASE_AND_OPERATIONS_V2.md) | Yo fijo instalación, observabilidad, actualización, recuperación y release. |
| [Plan maestro](planning/MASTER_PLAN_V2.md) | Yo fijo la secuencia de PR de 0 a producto final. |
| [Método de entrega](planning/DELIVERY_METHOD.md) | Yo fijo cómo ejecuto cada PR con arquitectura, evidencia y rollback. |
| [Trazabilidad](planning/TRACEABILITY.md) | Yo conecto requisitos, PR, pruebas y evidencia. |
| [Riesgos](planning/RISK_REGISTER.md) | Yo mantengo severidad, mitigación y gates de release. |
| [Decisiones abiertas](planning/OPEN_DECISIONS.md) | Yo registro lo que necesita hardware, benchmark o preferencia. |

## Repositorios y autoridad

- Yo mantengo [`SaintWyss/Wyss`](https://github.com/SaintWyss/Wyss) como autoridad, orquestador, política A–D, voz, Android, calendario, recordatorios, temporizadores, Spotify y notificaciones.
- Yo mantengo este repositorio como firmware de la pantalla y edge doméstico de baja latencia.
- Yo conservo [`esp32-smart-light-panel`](https://github.com/SaintWyss/esp32-smart-light-panel) como baseline físico y evidencia del camino Tuya probado.

## Estado

Yo declaro esta documentación como especificación de destino. Yo no afirmo que las capacidades v2 estén implementadas hasta que la trazabilidad tenga evidencia física y todos los gates de release estén aprobados.
