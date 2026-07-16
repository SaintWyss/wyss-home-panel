# Operación

## Instalación

Yo uso Arch/CachyOS, Python 3.12+, PlatformIO y OpenSSL. Yo ejecuto `scripts/create_identity.sh`, completo `config/local.toml` y `.env`, y luego ejecuto `scripts/install_bridge.sh`.

## Verificación

```bash
systemctl --user status wyss-panel-bridge
journalctl --user -u wyss-panel-bridge -f
curl --cacert config/private/ca.crt https://IP-DE-LA-NETBOOK:8443/health
pio run
```

Yo verifico el panel en este orden:

1. Yo confirmo que la retroiluminación y el táctil funcionan.
2. Yo confirmo `WYSS EN LÍNEA` en la esquina superior derecha.
3. Yo toco encendido y compruebo respuesta visual inmediata.
4. Yo confirmo `verified` y un RTT menor a 150 ms.
5. Yo desconecto la Wi-Fi y compruebo rollback sin estado falso.
6. Yo pruebo una intención de riesgo B y confirmo que aparece el modal.

## Recuperación

Yo conservo el respaldo original ya verificado con SHA-256 `842e75471b532f343886b6cf597e1ea57e8e807d55d48242157a53737628a7da`. Yo no lo publico porque puede contener datos específicos de la placa.

Yo restauro por USB sólo si el firmware no inicia. Yo no activo eFuses de seguridad hasta completar las pruebas de recuperación y conservar dos copias verificadas del respaldo.

