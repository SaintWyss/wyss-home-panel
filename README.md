# Wyss Home Panel

Yo convierto una Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2 (800×480, N16R8) en la superficie física de Wyss para el hogar. Yo respondo al tacto antes de esperar la red, mantengo las credenciales sensibles en la netbook y exijo confirmación cuando la política de Wyss lo decide.

## Resultado

Yo entrego una base completa v1.0.0 con:

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

Yo valido el dominio C++ y el puente Python con:

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

Yo verifiqué la compilación completa de producción con PlatformIO: usa 96.048 bytes de RAM
(29,3 %) y 1.574.789 bytes de Flash (24,0 %). Yo también verifiqué el dominio C++ con
advertencias tratadas como errores y las pruebas asíncronas del puente.

## Fuentes y procedencia

Yo reutilizo únicamente el conocimiento probado de [esp32-smart-light-panel](https://github.com/SaintWyss/esp32-smart-light-panel): pinout, puerto LVGL y mediciones físicas. Yo no copio sus credenciales ni su Flash. Yo baso el controlador de placa en [ESP32 Display Panel de Espressif](https://github.com/esp-arduino-libs/ESP32_Display_Panel), la interfaz en [LVGL](https://github.com/lvgl/lvgl), el hardware en la [documentación oficial de Waveshare](https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-7) y el streaming doméstico en la [API WebSocket de Home Assistant](https://developers.home-assistant.io/docs/api/websocket/).

Yo publico el proyecto bajo Apache-2.0 y mantengo las dependencias de terceros bajo sus licencias originales.

## Evolución Wyss Home v2.0.0

Yo documenté el producto final que conecta Wyss PC, Android y esta pantalla como una sola experiencia de clase Jarvis. Yo mantengo a [`SaintWyss/Wyss`](https://github.com/SaintWyss/Wyss) como autoridad de planes, política, voz y auditoría; yo convierto este repositorio en el edge doméstico y cuerpo físico de Wyss.

Yo no declaro esa versión implementada todavía. Yo concentro la especificación, arquitectura UML, protocolo, UX, integraciones, seguridad, pruebas, operación, roadmap por PR y trazabilidad en el [índice de producto v2](docs/README.md).
