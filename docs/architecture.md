# Arquitectura

## Decisión

Yo uso arquitectura hexagonal para que la lógica del panel no dependa del hardware ni de los proveedores. Yo aplico SOLID separando una razón de cambio por adaptador, invirtiendo las dependencias hacia puertos pequeños y permitiendo reemplazar Tuya por Home Assistant sin modificar el dominio.

## UML de componentes

```mermaid
flowchart LR
  Person[Yo, usuario] --> LVGL[Adaptador LVGL]
  LVGL --> App[PanelService]
  App --> Policy[EdgePolicy]
  App --> CommandPort[Puerto CommandPort]
  CommandPort --> WS[Adaptador WSS]
  WS --> API[Bridge FastAPI]
  API --> Session[SessionService]
  Session --> DevicePort[Puerto DeviceGateway]
  Session --> OrchestratorPort[Puerto OrchestratorGateway]
  DevicePort --> Tuya[Tuya LAN]
  DevicePort --> HA[Home Assistant]
  OrchestratorPort --> Wyss[Wyss Core]
```

## UML de clases

```mermaid
classDiagram
  class PanelService {
    +fast_action(entity, action, brightness)
    +submit_intent(text)
    +receive_plan(plan)
    +answer_plan(accepted)
    +reconcile_device(state)
    +tick()
  }
  class EdgePolicy {
    +allows_fast_path(command) bool
    +requires_confirmation(risk) bool
  }
  class CommandPort {
    <<interface>>
    +send_fast(command) bool
    +send_intent(intent) bool
    +confirm(plan, accepted, risk) bool
  }
  class ViewPort {
    <<interface>>
    +render_devices(devices)
    +render_plan(plan)
    +render_execution(update)
  }
  class BridgeClient
  class LvglPanelView
  class SessionService {
    +handle(message) responses
    +initial_snapshot() snapshot
  }
  class DeviceGateway {
    <<interface>>
    +snapshot(entities)
    +execute(command)
  }
  class OrchestratorGateway {
    <<interface>>
    +submit_intent(id, text)
    +answer_plan(id, accepted)
  }
  PanelService --> EdgePolicy
  PanelService --> CommandPort
  PanelService --> ViewPort
  CommandPort <|.. BridgeClient
  ViewPort <|.. LvglPanelView
  SessionService --> DeviceGateway
  SessionService --> OrchestratorGateway
```

## UML de secuencia rápida

```mermaid
sequenceDiagram
  actor Me as Yo
  participant UI as LVGL
  participant App as PanelService
  participant Bridge as Bridge local
  participant Light as Luz local
  Me->>UI: Toco encender
  UI->>App: fast_action()
  App->>UI: Pinto estado optimista
  App->>Bridge: command.fast por WSS
  Bridge->>Bridge: Autentico, limito e idempotizo
  Bridge->>Light: Ejecuto por LAN
  Light-->>Bridge: Estado real
  Bridge-->>App: state.changed + verified
  App->>UI: Reconcilio sin parpadeo
```

## UML de secuencia orquestada

```mermaid
sequenceDiagram
  actor Me as Yo
  participant Panel as Panel
  participant Bridge as Bridge
  participant Wyss as Wyss
  Me->>Panel: Escribo una intención
  Panel->>Bridge: intent.submit
  Bridge->>Wyss: POST /api/ask
  Wyss-->>Bridge: Plan + riesgo
  Bridge-->>Panel: plan.proposed
  Panel-->>Me: Muestro resumen y pasos
  Me->>Panel: Confirmo
  Panel->>Bridge: plan.answer
  Bridge->>Wyss: POST /api/confirm/{id}
  Wyss-->>Bridge: Ejecución auditada
  Bridge-->>Panel: execution.update
```

## UML de estados

```mermaid
stateDiagram-v2
  [*] --> Offline
  Offline --> Discovering: Yo tengo configuración
  Discovering --> Online: TLS + token válidos
  Online --> Optimistic: Yo toco una acción rápida
  Optimistic --> Verified: Yo recibo estado real
  Optimistic --> Online: Yo hago rollback a 2,5 s
  Online --> Planning: Yo envío una intención
  Planning --> AwaitingConfirmation: Riesgo B o C
  AwaitingConfirmation --> Executing: Yo confirmo
  AwaitingConfirmation --> Online: Yo cancelo
  Executing --> Verified: Wyss verifica
  Verified --> Online
  Online --> Offline: Yo pierdo la conexión
```

## Despliegue

```mermaid
flowchart TB
  subgraph Panel[ESP32-S3 N16R8]
    Touch[GT911] --> Firmware[Firmware LVGL]
    Firmware --> RGB[Pantalla RGB 800x480]
  end
  subgraph Netbook[Netbook Linux]
    Bridge[Bridge TLS]
    Wyss[Wyss Core]
  end
  subgraph LAN[Red doméstica]
    Bulb[Foco Tuya]
    HA[Home Assistant opcional]
  end
  Firmware <-->|WSS 8443| Bridge
  Bridge <-->|HTTP local autenticado| Wyss
  Bridge <-->|Tuya 3.3 o HA API| LAN
```

## Runtime v2 activo

El composition root activa v2 sólo mediante feature flags. El firmware de producción compila el
parser y el cliente v2, abre `/v2/client` y aplica snapshot+deltas sobre LVGL; PC, Android y panel
observan la misma proyección. El listener v1 permanece como rollback y no requiere migrar NVS.
El build verificado usa 146.664 bytes de RAM y 1.612.493 bytes de Flash.

Spotify respeta la misma frontera: OAuth, refresh y revocación pertenecen a Wyss. Home Edge sólo
traduce su contrato de media a la proyección `spotify` y a `capability.command`; PC, Android y panel
nunca reciben access/refresh tokens ni conocen endpoints del proveedor.

Yo definí ports pequeños para hogar, luces, proyecciones, eventos de clientes, media, clima,
Calendar, recordatorios, timers, notificaciones, voz y cámaras en `bridge/.../ports_v2.py`. Los DTOs
permanecen en dominio y ningún port importa adapters. `tools/check_architecture.py` bloquea en Python
y C++ cualquier dependencia que apunte desde dominio, protocolo, ports o aplicación hacia afuera.

El envelope, límites y compatibilidad están documentados en [Protocol v2](contracts/PROTOCOL_V2.md)
y fijados por el [schema versionado](../schemas/protocol-v2-envelope.schema.json). Python y C++
consumen los mismos fixtures de replay, revisión, snapshots, errores, duplicados y límites.
