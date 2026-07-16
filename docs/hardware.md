# Hardware validado

Yo apunto exclusivamente a la Waveshare ESP32-S3-Touch-LCD-7 Rev. 1.2 con ESP32-S3, 16 MB de Flash, 8 MB de PSRAM, LCD RGB 800×480 y táctil capacitivo GT911. Yo mantengo el pinout que ya validé físicamente en `esp32-smart-light-panel`.

| Señal | Recurso que uso |
| --- | --- |
| I²C SDA / SCL | GPIO 8 / GPIO 9 |
| Interrupción táctil | GPIO 4 |
| Expansor I/O | CH422G |
| Retroiluminación | CH422G, bit 2 |
| Reset LCD | CH422G, bit 3 |
| Reset táctil | CH422G, bit 1 |
| DE / HSYNC / VSYNC / PCLK | GPIO 5 / 46 / 3 / 7 |
| Resolución / reloj de píxel | 800×480 / 16 MHz, PCLK invertido |

Yo conservo la asignación completa del bus RGB en `firmware/include/esp_panel_board_custom_conf.h`; esa cabecera es la fuente ejecutable y evita que yo duplique valores en la documentación.

## Límites eléctricos

Yo alimento la pantalla por uno solo de sus conectores USB-C con una fuente estable de 5 V y al menos 2 A. Yo no conecto simultáneamente una fuente externa y otra alimentación sin comprobar masas y ruta de potencia. Yo no conecto periféricos de 5 V directamente a GPIO del ESP32-S3: su lógica es de 3,3 V.

## Recuperación

Yo conservo fuera del repositorio el respaldo de fábrica cuya suma SHA-256 es `842e75471b532f343886b6cf597e1ea57e8e807d55d48242157a53737628a7da`. Yo pruebo BOOT y RESET antes de cualquier cambio irreversible y no activo eFuses durante la instalación doméstica.
