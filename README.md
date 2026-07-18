# Wyss Home Panel

Yo convierto una Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2 (800×480, N16R8) en la superficie física de Wyss para el hogar. Yo respondo al tacto antes de esperar la red, mantengo las credenciales sensibles en la netbook y exijo confirmación cuando la política de Wyss lo decide.

## Baseline v1 preservado

Yo preservo una base completa v1.0.0 con:

- firmware ESP32-S3 con LVGL, doble framebuffer, tareas separadas por núcleo y actualización diferencial;
- puente local TLS para Tuya LAN o Home Assistant;
- integración del flujo `intención → plan → política → confirmación → ejecución → auditoría` de Wyss;
- camino rápido limitado a luces y escenas explícitamente autorizadas;
- estado optimista inmediato con reconciliación y rollback automático a los 2,5 segundos;
- aprovisionamiento USB sin secretos en Git, token aleatorio de 256 bits y CA local;
- pruebas de dominio y puente, CI, documentación UML y decisiones arquitectónicas;
- suspensión automática de la retroiluminación después de cinco minutos sin interacción.

Yo interpreto “latencia cero” como latencia perceptual cero: pinto la respuesta local en menos de 50 ms y verifico el resultado remoto después. En el firmware anterior de esta misma placa yo ya medí ciclos LVGL/táctil de aproximadamente 0,4 ms y respuestas Tuya LAN de 22–41 ms; conservo ese camino de hardware y establezco presupuestos reproducibles en [rendimiento](docs/performance.md).

## Arquitectura

Yo mantengo el dominio independiente de LVGL, WebSocket, Tuya, Home Assistant y FastAPI. Yo documento el detalle y los diagramas UML en [arquitectura](docs/architecture.md).

```text
firmware/  → cliente táctil, política de borde y respuesta optimista
bridge/    → autenticación, idempotencia, proveedores y adaptador Wyss
config/    → plantilla sin secretos
docs/      → UML, seguridad, protocolo, rendimiento y operación
scripts/   → identidad TLS e instalación reproducible
tools/     → aprovisionamiento USB de una sola vez
```

## Puesta en marcha

Yo preparo primero la identidad local:

```bash
cp config/bridge.example.toml config/local.toml
cp .env.example .env
./scripts/create_identity.sh 192.168.1.20 wyss-panel-living
```

Yo copio en `config/local.toml` el `token_sha256` mostrado, completo `.env` y el proveedor, e instalo el puente:

```bash
./scripts/install_bridge.sh
curl --cacert config/private/ca.crt https://192.168.1.20:8443/health
```

Yo compilo y cargo el firmware desde PlatformIO:

```bash
pio run
pio run --target upload
```

Yo aprovisiono el panel una sola vez:

```bash
python tools/provision.py \
  --port /dev/serial/by-id/usb-1a86_USB_Single_Serial_5C37247963-if00 \
  --bridge-url wss://192.168.1.20:8443/v1/panel \
  --panel-id wyss-panel-living \
  --primary-entity light.living \
  --token-file config/private/panel-token.once \
  --ca-file config/private/ca.crt
```

Yo detallo el proceso, el diagnóstico y la recuperación en [operación](docs/operations.md).
Yo documento el modelo exacto, su pinout validado y los límites eléctricos en [hardware](docs/hardware.md).

## Calidad

Yo valido el baseline automatizado completo con un único comando reproducible. El runner fija
versiones y mantiene los entornos de uv, PlatformIO y CMake bajo `.cache/wyss-baseline/`:

```bash
./scripts/verify_baseline.sh automated
```

El gate total incluye además la evidencia física versionada. `all` retorna 40 hasta que esa
evidencia exista y su estado sea `VERIFIED`:

```bash
./scripts/verify_baseline.sh all
```

Los comandos individuales equivalentes para diagnóstico son:

```bash
python tools/doctor.py
cmake -S . -B build && cmake --build build && ctest --test-dir build
python -m pip install uv==0.11.18
uv sync --project bridge --locked --extra dev
uv run --project bridge --locked --extra dev ruff check bridge tools/check_docs.py tools/doctor.py
uv run --project bridge --locked --extra dev mypy bridge/src
uv run --project bridge --locked --extra dev pytest bridge/tests
python tools/check_docs.py
pio run -e waveshare_esp32_s3_touch_lcd_7
```

Las versiones mínimas y exactas que forman la línea base están registradas en
`config/baseline-versions.toml`; `bridge/uv.lock` congela el entorno Python. Los fixtures dorados
de protocolo v1 son compartidos por las pruebas Python y C++.

El baseline también compila un simulador headless con el mismo LVGL 8.4.0 del firmware y compara
diez frames 800×480 contra `tests/fixtures/ui_visual_manifest.txt`. Las capturas quedan bajo el
directorio CMake en `ui-snapshots/`; una diferencia no aprobada falla `ui_visual_tests`.

Yo verifiqué la compilación completa de producción con PlatformIO: usa 145.992 bytes de RAM
(44,6 %) y 1.599.445 bytes de Flash (24,4 %), incluido el heap LVGL de 96 KiB requerido por el
shell v2. Yo también verifiqué cinco pruebas C++ —incluida la regresión visual— y las 116 pruebas
del puente.

## Fuentes y procedencia

Yo reutilizo únicamente el conocimiento probado de [esp32-smart-light-panel](https://github.com/SaintWyss/esp32-smart-light-panel): pinout, puerto LVGL y mediciones físicas. Yo no copio sus credenciales ni su Flash. Yo baso el controlador de placa en [ESP32 Display Panel de Espressif](https://github.com/esp-arduino-libs/ESP32_Display_Panel), la interfaz en [LVGL](https://github.com/lvgl/lvgl), el hardware en la [documentación oficial de Waveshare](https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-7) y el streaming doméstico en la [API WebSocket de Home Assistant](https://developers.home-assistant.io/docs/api/websocket/).

Yo publico el proyecto bajo Apache-2.0 y mantengo las dependencias de terceros bajo sus licencias originales.

## Evolución Wyss Home v2.0.0

Yo documenté el producto final que conecta Wyss PC, Android y esta pantalla como una sola experiencia de clase Jarvis. Yo mantengo a [`SaintWyss/Wyss`](https://github.com/SaintWyss/Wyss) como autoridad de planes, política, voz y auditoría; yo convierto este repositorio en el edge doméstico y cuerpo físico de Wyss.

La implementación automatizada de v2.0.0 está integrada y conserva el camino v1. La promoción
final continúa retenida hasta completar los gates físicos/externos, el soak de 72 horas, la firma
de artefactos y el smoke de release documentados en el [índice de producto v2](docs/README.md).
